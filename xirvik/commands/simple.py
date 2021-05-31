"""Mirror (copy data from remote to local) helper."""
from base64 import b64encode
from logging.handlers import SysLogHandler
from netrc import netrc
from os import close as close_fd, listdir, makedirs, remove as rm
from os.path import (basename, expanduser, isdir, join as path_join, realpath,
                     splitext)
from tempfile import mkstemp
import argparse
import logging
import signal
import socket
import sys

from requests.exceptions import HTTPError
from unidecode import unidecode
import argcomplete
import requests

from xirvik.util import ReadableDirectoryListAction, ctrl_c_handler


def start_torrents() -> None:
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
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    verbose = args.debug or args.verbose
    log.setLevel(logging.INFO)

    if verbose:
        channel = logging.StreamHandler(
            sys.stdout if args.verbose else sys.stderr)

        channel.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        channel.setLevel(logging.INFO if args.verbose else logging.DEBUG)
        log.addHandler(channel)

        if args.debug:
            log.setLevel(logging.DEBUG)

    if args.syslog:
        try:
            syslogh = SysLogHandler(address='/dev/log')
        except (OSError, socket.error):
            syslogh = SysLogHandler(address='/var/run/syslog',
                                    facility=SysLogHandler.LOG_USER)
            syslogh.ident = 'xirvik-start-torrents'
            logging.INFO = logging.WARNING

        syslogh.setFormatter(
            logging.Formatter('%(name)s[%(process)d]: %(message)s'))
        syslogh.setLevel(logging.DEBUG if args.debug else logging.INFO)
        log.addHandler(syslogh)

    user_pass = netrc(args.netrc_path).authenticators(args.host[0])
    if not user_pass:
        print((f'Cannot find host {args.host[0]} in netrc. Specify user name '
               'and password'),
              file=sys.stderr)
        sys.exit(1)
    _user, _, _password = user_pass
    post_url = ('https://{host:s}:{port:d}/rtorrent/php/'
                'addtorrent.php?'.format(host=args.host[0], port=args.port[0]))
    form_data = {}
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
            with open(item, 'rb') as torrent_file:
                # Because the server does not understand filename*=UTF8 syntax
                # https://github.com/kennethreitz/requests/issues/2117
                # This is not a huge concern, as the API's "Get .torrent" does
                # not return the file with its original name either
                filename = unidecode(torrent_file.name)
                files = dict(torrent_file=(
                    filename,
                    torrent_file,
                ))
                try:
                    log.info('Uploading torrent %s (actual name: "%s")',
                             basename(item), basename(filename))
                except OSError:
                    pass
                resp = requests.post(post_url, data=form_data, files=files)
                try:
                    resp.raise_for_status()
                except HTTPError as e:
                    log.error('Caught exception: %s', e)
                # Delete original only after successful upload
                log.debug('Deleting %s', old)
                rm(old)


def add_ftp_user() -> int:
    """Adds an FTP user."""
    log = logging.getLogger('xirvik')
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', required=True)
    parser.add_argument('-P', '--password', required=True)
    parser.add_argument('-r', '--root-directory', default='/')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-H', '--host', required=True)
    parser.add_argument('-p', '--port', type=int, default=443)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    verbose = args.debug or args.verbose
    log.setLevel(logging.INFO)
    if verbose:
        channel = logging.StreamHandler(
            sys.stdout if args.verbose else sys.stderr)
        channel.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        channel.setLevel(logging.INFO if args.verbose else logging.DEBUG)
        log.addHandler(channel)
        if args.debug:
            log.setLevel(logging.DEBUG)
    uri = (f'https://{args.host}:{args.port:d}/userpanel/index.php/'
           'ftp_users/add_user')
    rootdir = args.root_directory if args.root_directory.startswith(
        '/') else f'/{args.root_directory}'
    # Setting read_only=yes does not appear to work
    r = requests.post(uri,
                      data=dict(username=args.username,
                                password_1=args.password,
                                root_folder=rootdir,
                                read_only='no'))
    try:
        r.raise_for_status()
    except HTTPError as e:
        log.exception(e)
        return 1
    return 0


def delete_ftp_user() -> int:
    """Deletes an FTP user."""
    log = logging.getLogger('xirvik')
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', required=True)
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-H', '--host', required=True)
    parser.add_argument('-p', '--port', type=int, default=443)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    verbose = args.debug or args.verbose
    log.setLevel(logging.INFO)
    if verbose:
        channel = logging.StreamHandler(
            sys.stdout if args.verbose else sys.stderr)
        channel.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        channel.setLevel(logging.INFO if args.verbose else logging.DEBUG)
        log.addHandler(channel)
        if args.debug:
            log.setLevel(logging.DEBUG)
    user = b64encode(args.username.encode('utf-8')).decode('utf-8')
    uri = (f'https://{args.host}:{args.port:d}/userpanel/index.php/ftp_users/'
           f'delete/{user}')
    r = requests.get(uri)
    try:
        r.raise_for_status()
    except HTTPError as e:
        log.exception(e)
        return 1
    return 0


def authorize_ip() -> int:
    """Authorises an IP for access to the VM via SSH, removing the previous."""
    log = logging.getLogger('xirvik')
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-H', '--host', required=True)
    parser.add_argument('-p', '--port', type=int, default=443)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    verbose = args.debug or args.verbose
    log.setLevel(logging.INFO)
    if verbose:
        channel = logging.StreamHandler(
            sys.stdout if args.verbose else sys.stderr)
        channel.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        channel.setLevel(logging.INFO if args.verbose else logging.DEBUG)
        log.addHandler(channel)
        if args.debug:
            log.setLevel(logging.DEBUG)
    uri = (f'https://{args.host}:{args.port:d}/userpanel/index.php/'
           'virtual_machine/authorize_ip')
    r = requests.get(uri)
    try:
        r.raise_for_status()
    except HTTPError as e:
        log.exception(e)
        return 1
    return 0


def fix_rtorrent() -> int:
    """
    Restarts the rtorrent service in case ruTorrent cannot connect to it. Not
    guaranteed to fix anything!
    """
    log = logging.getLogger('xirvik')
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-H', '--host', required=True)
    parser.add_argument('-p', '--port', type=int, default=443)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    verbose = args.debug or args.verbose
    log.setLevel(logging.INFO)
    if verbose:
        channel = logging.StreamHandler(
            sys.stdout if args.verbose else sys.stderr)
        channel.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        channel.setLevel(logging.INFO if args.verbose else logging.DEBUG)
        log.addHandler(channel)
        if args.debug:
            log.setLevel(logging.DEBUG)
    log.warning('No guarantees this will work!')
    uri = (f'https://{args.host}:{args.port:d}/userpanel/index.php/services/'
           'restart/rtorrent')
    r = requests.get(uri)
    try:
        r.raise_for_status()
    except HTTPError as e:
        log.exception(e)
        return 1
    return 0
