"""Mirror (copy data from remote to local) helper."""
from logging.handlers import SysLogHandler
from os import chmod, close as close_fd, listdir, makedirs, remove as rm, utime
from os.path import (basename, dirname, isdir, expanduser,
                     join as path_join, realpath, splitext)
from netrc import netrc
from tempfile import gettempdir, mkstemp
import argparse
import hashlib
import json
import logging
import os
import signal
import socket
import subprocess as sp
import sys

from lockfile import LockFile, NotLocked
from unidecode import unidecode
import requests

from xirvik.client import (
    TORRENT_PATH_INDEX,
    UnexpectedruTorrentError,
    ruTorrentClient,
)
from xirvik.log import cleanup, get_logger
from xirvik.sftp import SFTPClient
from xirvik.util import (
    ReadableDirectoryListAction,
    VerificationError,
    cleanup_and_exit,
    ctrl_c_handler,
    verify_torrent_contents,
)

_lock = None


def lock_ctrl_c_handler(signum, frame):
    """TERM signal/^C handler."""
    if _lock:
        try:
            _lock.release()
        except NotLocked:
            pass

    ctrl_c_handler(signum, frame)
    raise SystemExit('Signal raised')


def mirror(sftp_client,
           rclient,
           path='.',
           destroot='.',
           keep_modes=True,
           keep_times=True):
    """
    Mirror a remote directory to local.

    sftp_client must be a valid xirvik.sftp.SFTPClient instance.

    rclient must be a valid ruTorrentClient instance.

    path is the remote directory. destroot must be the location where
    destroot/path will be created (the path must not already exist).

    keep_modes and keep_times are boolean to ensure permissions and time
    are retained respectively.
    """
    cwd = sftp_client.getcwd()
    log = logging.getLogger('xirvik')

    for _path, info in sftp_client.listdir_attr_recurse(path=path):
        if info.st_mode & 0o700 == 0o700:
            continue

        dest_path = path_join(destroot, dirname(_path))
        dest = path_join(dest_path, basename(_path))

        if dest_path not in sftp_client._dircache:
            try:
                makedirs(dest_path)
            except OSError:
                pass
            sftp_client._dircache.append(dest_path)

        if isdir(dest):
            continue

        try:
            current_size = os.stat(dest).st_size
        except OSError:
            current_size = None

        if current_size is None or current_size != info.st_size:
            sess = rclient._session
            uri = '{}/downloads{}{}'.format(rclient.http_prefix,
                                            cwd, _path[1:])
            uri = uri.replace('#', '%23')
            log.info('Downloading {} -> {}'.format(uri, dest))

            r = sess.get(uri, stream=True)
            r.raise_for_status()
            try:
                total = int(r.headers.get('content-length'))
                log.info('Content-Length: {}'.format(total))
            except (KeyError, ValueError):
                total = None

            with open(dest, 'wb+') as f:
                dl = 0
                for chunk in r.iter_content(chunk_size=4096):
                    f.write(chunk)

                    dl += len(chunk)
                    done = int(50 * dl / total)
                    percent = (float(dl) / float(total)) * 100
                    args = ('=' * done, ' ' * (50 - done), percent,)
                    sys.stdout.write('\r[{}{}] {:.2f}%'.format(*args))
                    sys.stdout.flush()

            sys.stdout.write('\n')
        else:
            log.info('Skipping already downloaded file {}'.format(dest))

        # Okay to fix existing files even if they are already downloaded
        try:
            if keep_modes:
                chmod(dest, info.st_mode)
            if keep_times:
                utime(dest, (info.st_atime, info.st_mtime,))
        except IOError:
            pass


def mirror_main():
    """Entry point."""
    signal.signal(signal.SIGINT, lock_ctrl_c_handler)

    parser = argparse.ArgumentParser()

    parser.add_argument('-H', '--host', required=True)
    parser.add_argument('-P', '--port', type=int, default=22)
    parser.add_argument('-c', '--netrc-path', default=expanduser('~/.netrc'))
    parser.add_argument('-r', '--resume', action='store_true',
                        help='Resume incomplete files (experimental)')
    parser.add_argument('-T', '--move-to', required=True)
    parser.add_argument('-L', '--label', default='Seeding')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-s', '--syslog', action='store_true')
    parser.add_argument('--no-preserve-permissions', action='store_false')
    parser.add_argument('--no-preserve-times', action='store_false')
    parser.add_argument('--max-retries', type=int, default=10)
    parser.add_argument('remote_dir', metavar='REMOTEDIR', nargs=1)
    parser.add_argument('local_dir', metavar='LOCALDIR', nargs=1)

    args = parser.parse_args()
    log = get_logger('xirvik',
                     verbose=args.verbose,
                     debug=args.debug,
                     syslog=args.syslog)
    if args.debug:
        logs_to_follow = (
            'requests',
        )
        for name in logs_to_follow:
            _log = logging.getLogger(name)
            formatter = logging.Formatter('%(asctime)s - %(name)s - '
                                          '%(levelname)s - %(message)s')
            channel = logging.StreamHandler(sys.stderr)

            _log.setLevel(logging.DEBUG)
            channel.setLevel(logging.DEBUG)
            channel.setFormatter(formatter)
            _log.addHandler(channel)

    local_dir = realpath(args.local_dir[0])
    user, _, password = netrc(args.netrc_path).authenticators(args.host)
    sftp_host = 'sftp://{user:s}@{host:s}'.format(
        user=user,
        host=args.host,
    )

    lf_hash = hashlib.sha256(json.dumps(
        args._get_kwargs()).encode('utf-8')).hexdigest()
    lf_path = path_join(gettempdir(), 'xirvik-mirror-{}'.format(lf_hash))
    log.debug('Acquiring lock at {}.lock'.format(lf_path))
    _lock = LockFile(lf_path)
    if _lock.is_locked():
        psax = [x for x in
                sp.check_output(['ps', 'ax']).decode('utf-8').split('\n')
                if sys.argv[0] in x]
        if len(psax) == 1:
            log.info('Breaking lock')
            _lock.break_lock()
    _lock.acquire()
    log.info('Lock acquired')

    log.debug('Local directory to sync to: {}'.format(local_dir))
    log.debug('Read user and password from netrc file')
    log.debug('SFTP URI: {}'.format(sftp_host))

    client = ruTorrentClient(args.host,
                             user,
                             password,
                             max_retries=args.max_retries)

    assumed_path_prefix = '/torrents/{}'.format(user)
    look_for = '{}/{}/'.format(assumed_path_prefix, args.remote_dir[0])
    move_to = '{}/{}'.format(assumed_path_prefix, args.move_to)
    names = {}

    log.debug('Full completed directory path name: {}'.format(look_for))
    log.debug('Moving finished torrents to: {}'.format(move_to))

    log.info('Getting current torrent information (ruTorrent)')
    try:
        torrents = client.list_torrents()
    except requests.exceptions.ConnectionError as e:
        # Assume no Internet connection at this point
        log.error('Failed to connect: {}'.format(e))
        try:
            _lock.release()
        except NotLocked:
            pass
        cleanup_and_exit(1)

    for hash, v in torrents.items():
        if not v[TORRENT_PATH_INDEX].startswith(look_for):
            continue
        bn = basename(v[TORRENT_PATH_INDEX])
        names[bn] = (hash, v[TORRENT_PATH_INDEX],)

        log.info('Completed torrent "{}" found with hash {}'.format(bn, hash,))

    sftp_client_args = dict(
        hostname=args.host,
        username=user,
        password=password,
        port=args.port,
    )

    try:
        with SFTPClient(**sftp_client_args) as sftp_client:
            log.info('Verifying contents of {} with previous '
                     'response'.format(look_for))

            sftp_client.chdir(args.remote_dir[0])
            for item in sftp_client.listdir_iter(read_aheads=10):
                if item.filename not in names:
                    log.error('File or directory "{}" not found in previous '
                              'response body'.format(item.filename))
                    continue

                log.debug('Found matching torrent "{}" from ls output'.format(
                    item.filename))

            if not len(names.items()):
                log.info('Nothing found to mirror')
                _lock.release()
                cleanup_and_exit()

            mirror(sftp_client,
                   client,
                   destroot=local_dir,
                   keep_modes=not args.no_preserve_permissions,
                   keep_times=not args.no_preserve_times)
    except Exception as e:
        if args.debug:
            _lock.release()
            cleanup()
            raise e
        else:
            log.error(str(e))
        _lock.release()
        cleanup_and_exit()

    _all = names.items()
    exit_status = 0
    bad = []
    for bn, (hash, fullpath) in _all:
        # There is a warning that can get raised here by urllib3 if
        # Content-Disposition header's filename field has any
        # non-ASCII characters. It is ignorable as the content still gets
        # downloaded correctly
        log.info('Verifying "{}"'.format(bn))
        r, _ = client.get_torrent(hash)
        try:
            verify_torrent_contents(r.content, local_dir)
        except VerificationError as e:
            log.error('Could not verify "{}" contents against piece hashes '
                      'in torrent file'.format(bn))
            exit_status = 1
            bad.append(hash)

    # Move to _seeding directory and set label
    # Unfortunately, there is no method, via the API, to do this one HTTP
    #   request
    for bn, (hash, fullpath) in _all:
        if hash in bad:
            continue
        log.info('Moving "{}" to "{}" directory'.format(bn, move_to))
        try:
            client.move_torrent(hash, move_to)
        except UnexpectedruTorrentError as e:
            log.error(str(e))

    log.info('Setting label to "{}" for downloaded items'.format(args.label))

    client.set_label_to_hashes(hashes=[hash for bn, (hash, fullpath)
                                       in names.items() if hash not in bad],
                               label=args.label)

    if exit_status != 0:
        log.error('Could not verify torrent checksums')

    _lock.release()
    cleanup_and_exit(exit_status)


def start_torrents():
    """Uploads torrent files to the server."""
    signal.signal(signal.SIGINT, ctrl_c_handler)

    cache_dir = realpath(expanduser('~/.cache/xirvik'))

    if not isdir(cache_dir):
        makedirs(cache_dir)

    log = logging.getLogger('xirvik-start-torrents')
    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-c', '--netrc-path', default=expanduser('~/.netrc'))
    # parser.add_argument('-C', '--client', default='rutorrent3')
    parser.add_argument('-H', '--host', nargs=1, required=True)
    parser.add_argument('-p', '--port', nargs=1, default=[443])
    parser.add_argument('--start-stopped', action='store_true')
    parser.add_argument('-s', '--syslog', action='store_true')
    parser.add_argument('directory',
                        metavar='DIRECTORY',
                        action=ReadableDirectoryListAction,
                        nargs='*')

    args = parser.parse_args()
    verbose = args.debug or args.verbose
    log.setLevel(logging.INFO)

    if verbose:
        channel = logging.StreamHandler(sys.stdout if args.verbose
                                        else sys.stderr)

        channel.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        channel.setLevel(logging.INFO if args.verbose else logging.DEBUG)
        log.addHandler(channel)

        if args.debug:
            log.setLevel(logging.DEBUG)

    if args.syslog:
        try:
            syslogh = SysLogHandler(address='/dev/log')
        except (OSError, socket.error):
            syslogh = SysLogHandler(address='/var/run/syslog')
            logging.INFO = logging.WARNING

        syslogh.setFormatter(
            logging.Formatter('%(name)s[%(process)d]: %(message)s'))
        syslogh.setLevel(logging.DEBUG if args.debug else logging.INFO)
        log.addHandler(syslogh)

    try:
        user, _, password = netrc(args.netrc_path).authenticators(args.host[0])
    except TypeError:
        print('Cannot find host {} in netrc. Specify user name and '
              'password'.format(args.host[0]), file=sys.stderr)
        sys.exit(1)

    post_url = ('https://{host:s}:{port:d}/rtorrent/php/'
                'addtorrent.php?'.format(host=args.host[0], port=args.port[0]))
    form_data = {}
    exceptions_caught = []

    # rtorrent2/3 params
    # dir_edit - ?
    # tadd_label - Label for the torrents, more param: label=
    # torrent_file - Torrent file blob data

    if args.start_stopped:
        form_data['torrents_start_stopped'] = 'on'

    for d in args.directory:
        for item in listdir(d):
            if not item.lower().endswith('.torrent'):
                continue

            item = path_join(d, item)

            # Workaround for surrogates not allowed error, rename the file
            prefix = '{n:s}-'.format(n=splitext(basename(item))[0])
            fd, name = mkstemp(dir=cache_dir, prefix=prefix, suffix='.torrent')
            close_fd(fd)
            with open(name, 'wb') as w:
                with open(item, 'rb') as r:
                    w.write(r.read())
            old = item
            item = name

            with open(item, 'rb') as f:
                # Because the server does not understand filename*=UTF8 syntax
                # https://github.com/kennethreitz/requests/issues/2117
                # This is not a huge concern, as the API's "Get .torrent" does
                # not return the file with its original name either
                try:
                    filename = unidecode(f.name.decode('utf8'))
                except AttributeError:  # decode
                    filename = unidecode(f.name)

                files = dict(torrent_file=(filename, f,))
                log.info('Uploading torrent {} (actual name: "{}")'.format(
                    basename(item), basename(filename)))
                r = requests.post(post_url, data=form_data, files=files)

                try:
                    r.raise_for_status()
                except Exception as e:
                    log.error('Caught exception: {}'.format(e))

                # Delete original only after successful upload
                log.debug('Deleting {}'.format(old))
                rm(old)

    if exceptions_caught:
        log.error('Exceptions caught, exiting with failure status')
        cleanup_and_exit(1)
