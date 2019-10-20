"""General utility module."""
from hashlib import sha1
from hmac import compare_digest
from os import R_OK, access, environ, stat
from os.path import isdir, join as path_join, realpath
import argparse
import platform
import struct
import sys

from bencodepy import decode as bdecode
import six

from xirvik.log import cleanup

__all__ = (
    'cleanup_and_exit',
    'ctrl_c_handler',
    'VerificationError',
    'verify_torrent_contents',
    'ReadableDirectoryListAction',
)


class ReadableDirectoryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir = values

        if not isdir(prospective_dir):
            raise argparse.ArgumentTypeError(
                '%s is not a valid directory' % (prospective_dir,))

        # Since macOS 10.15, the Python binary will need access to this
        # directory and a prompt from TCC must appear for this to work
        # Because of TCC becoming more strict, hecking with access() is not
        # reliable on macOS
        if platform.system() == 'Darwin':
            return

        if access(prospective_dir, R_OK):
            setattr(namespace, self.dest, realpath(prospective_dir))
            return

        username = environ['USER']
        msg = '{} is not a readable directory (checking as user {})'.format(
            prospective_dir, username)
        raise argparse.ArgumentTypeError(msg)


class ReadableDirectoryListAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        dirs = []
        kwa = dict(self._get_kwargs())
        parent = ReadableDirectoryAction(**kwa)

        for prospective_dir in values:
            ns = argparse.Namespace()
            ns.directory = prospective_dir
            parent(parser, ns, prospective_dir, option_string)
            dirs.append(ns.directory)

        setattr(namespace, self.dest, dirs)


def cleanup_and_exit(status=0):
    """Called instead of sys.exit(). status is the integer to exit with."""
    cleanup()
    sys.exit(status)


def ctrl_c_handler(signum, frame):
    """Used as a TERM signal handler. Arguments are ignored."""
    cleanup()
    raise SystemExit('Signal raised')


def _chunks(l, n):
    # Source: http://stackoverflow.com/a/312464/374110
    for i in range(0, len(l), n):
        yield l[i:i + n]


def _get_torrent_pieces(filenames, basepath, piece_length):
    # Yes this is a generator and should not be used any other way (i.e. do not
    # wrap in list()).
    buf = b''
    p_delta = piece_length

    for name in filenames:
        name = path_join(basepath, name)
        try:
            size = stat(name).st_size
        except OSError:
            yield None

        if size <= piece_length and p_delta > size:
            with open(name, 'rb') as f:
                tmp = f.read()
                p_delta -= len(tmp)

                if p_delta <= 0:
                    p_delta = piece_length

                buf += tmp

            continue

        try:
            with open(name, 'rb') as f:
                while True:
                    tmp = f.read(p_delta)
                    p_delta -= len(tmp)

                    if not tmp:
                        break

                    buf += tmp

                    if len(tmp) < p_delta:
                        break

                    if p_delta <= 0:
                        yield buf
                        buf = b''
                        p_delta = piece_length
        except IOError:
            yield None

    # Very last set of bytes of the last file, and this will be <= piece size
    # If this is not returned, a false positive can be given if the last
    # file's last piece is not valid
    if buf:
        yield buf


class VerificationError(Exception):
    """Raised when an error occurs in verify_torrent_contents()."""

    pass


def verify_torrent_contents(torrent_file, path):
    """
    Verify torrent contents.

    Pass a torrent file path and the path to check.
    """
    orig_path = path

    if hasattr(torrent_file, 'seek') and hasattr(torrent_file, 'read'):
        torrent_file.seek(0)
        torrent = bdecode(torrent_file.read())
    else:
        try:
            with open(torrent_file, 'rb') as f:
                torrent = bdecode(f.read())
        except (IOError, TypeError, ValueError):
            # ValueError for 'embedded null byte' in Python 3.5
            torrent = bdecode(torrent_file)

    path = path_join(path, torrent[b'info'][b'name'].decode('utf-8'))
    is_a_file = False
    try:
        with open(path, 'rb'):
            is_a_file = True
    except IOError:
        pass

    if not isdir(path) and not is_a_file:
        raise IOError('Path specified for torrent data is invalid')

    piece_length = torrent[b'info'][b'piece length']
    piece_hashes = torrent[b'info'][b'pieces']
    piece_hashes = struct.unpack('<{}B'.format(len(piece_hashes)),
                                 piece_hashes)
    piece_hashes = _chunks(piece_hashes, sha1().digest_size)

    try:
        filenames = ('/'.join([y.decode('utf-8') for y in x[b'path']])
                     for x in torrent[b'info'][b'files'])
    except KeyError as e:
        if e.args[0] != b'files':
            raise e

        # Single file torrent, never has a directory
        filenames = [path]
        path = orig_path

    pieces = _get_torrent_pieces(filenames, path, piece_length)

    for known_hash, piece in zip(piece_hashes, pieces):
        if six.PY2:
            known_hash = ''.join([six.int2byte(x) for x in known_hash])
        else:
            known_hash = bytes(known_hash)

        try:
            file_hash = sha1(piece).digest()
        except TypeError:
            raise VerificationError('Unable to get hash for piece')

        if not compare_digest(known_hash, file_hash):
            raise VerificationError('Computed hash does not match torrent '
                                    'file\'s hash')
