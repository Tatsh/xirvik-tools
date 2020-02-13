"""General utility module."""
from hashlib import sha1
from hmac import compare_digest
from os import R_OK, access, environ, stat
from os.path import isdir, join as path_join, realpath
from typing import (Any, BinaryIO, Iterator, List, NoReturn, Optional,
                    Sequence, TypeVar, Union, cast)
import argparse
import platform
import struct
import sys

from benc import decode as bdecode

__all__ = (
    'cleanup_and_exit',
    'ctrl_c_handler',
    'VerificationError',
    'verify_torrent_contents',
    'ReadableDirectoryListAction',
)

T = TypeVar('T')


class ReadableDirectoryAction(argparse.Action):
    """Checks if a directory argument is a directory and is readable."""
    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 values: Optional[Union[str, Sequence[Any]]],
                 option_string: Optional[str] = None) -> None:
        prospective_dir = values
        if not isdir(cast(str, prospective_dir)):
            raise argparse.ArgumentTypeError('%s is not a valid directory' %
                                             (prospective_dir, ))
        # Since macOS 10.15, the Python binary will need access to this
        # directory and a prompt from TCC must appear for this to work
        # Because of TCC becoming more strict, hecking with access() is not
        # reliable on macOS
        if platform.system() == 'Darwin':
            return
        if access(cast(str, prospective_dir), R_OK):
            setattr(namespace, self.dest, realpath(cast(str, prospective_dir)))
            return
        username = environ['USER']
        raise argparse.ArgumentTypeError(
            f'{prospective_dir} is not a readable directory (checking as user '
            f'{username})')


class ReadableDirectoryListAction(argparse.Action):
    """
    Checks if a list of directories argument is a directory and all are
    readable..
    """
    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 values: Optional[Union[str, Sequence[Any]]],
                 option_string: Optional[str] = None) -> None:
        dirs = []
        kwa = dict(self._get_kwargs())
        parent = ReadableDirectoryAction(**kwa)

        for prospective_dir in cast(Sequence[Any], values):
            ns = argparse.Namespace()
            ns.directory = prospective_dir
            parent(parser, ns, prospective_dir, option_string)
            dirs.append(ns.directory)

        setattr(namespace, self.dest, dirs)


def cleanup_and_exit(status: int = 0) -> NoReturn:
    """Called instead of sys.exit(). status is the integer to exit with."""
    sys.exit(status)


def ctrl_c_handler(signum: int, frame: Any) -> NoReturn:
    """Used as a TERM signal handler. Arguments are ignored."""
    raise SystemExit('Signal raised')


def _chunks(l: Sequence[T], n: int) -> Iterator[Sequence[T]]:
    # Source: http://stackoverflow.com/a/312464/374110
    for i in range(0, len(l), n):
        yield l[i:i + n]


def _get_torrent_pieces(filenames: Sequence[str], basepath: str,
                        piece_length: int) -> Iterator[Optional[bytes]]:
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


def verify_torrent_contents(torrent_file: Union[str, BinaryIO, bytes],
                            path: str) -> None:
    """
    Verify torrent contents.

    Pass a torrent file path and the path to check.
    """
    orig_path = path

    if hasattr(torrent_file, 'seek') and hasattr(torrent_file, 'read'):
        cast(BinaryIO, torrent_file).seek(0)
        torrent = bdecode(cast(BinaryIO, torrent_file).read())
    else:
        try:
            with open(cast(str, torrent_file), 'rb') as f:
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
        filenames: Union[Iterator[str], List[str]] = ('/'.join(
            [y.decode('utf-8')
             for y in x[b'path']]) for x in torrent[b'info'][b'files'])
    except KeyError as e:
        if e.args[0] != b'files':
            raise e

        # Single file torrent, never has a directory
        filenames = [path]
        path = orig_path

    pieces = _get_torrent_pieces(list(filenames), path, piece_length)

    for known_hash, piece in zip(piece_hashes, pieces):
        known_hash = bytes(known_hash)

        try:
            file_hash = sha1(cast(bytes, piece)).digest()
        except TypeError:
            raise VerificationError('Unable to get hash for piece')

        if not compare_digest(known_hash, file_hash):
            raise VerificationError('Computed hash does not match torrent '
                                    'file\'s hash')
