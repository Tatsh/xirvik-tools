from hashlib import sha1
from hmac import compare_digest
from os import stat
from os.path import isdir, join as path_join
import struct
import sys

from bencodepy import decode as bdecode

from xirvik.logging import cleanup


def cleanup_and_exit(status=0):
    cleanup()
    sys.exit(status)


def ctrl_c_handler(signum, frame):
    cleanup()
    raise SystemExit('Signal raised')


def _chunks(l, n):
    """
    http://stackoverflow.com/a/312464/374110
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]


def _get_torrent_pieces(filenames, basepath, piece_length):
    """
    Yes this is a generator and should not be used any other way (i.e. do not
    wrap in list()).
    """
    buf = b''
    p_delta = piece_length

    for name in filenames:
        name = path_join(basepath, name)
        try:
            size = stat(name).st_size
        except IOError:
            yield None

        if size <= piece_length and p_delta > size:
            with open(name, 'rb') as f:
                tmp = f.read()
                p_delta -= len(tmp)

                if p_delta <= 0:
                    p_delta = piece_length

                buf += tmp

            continue

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


class VerificationError(Exception):
    pass


def verify_torrent_contents(torrent_file, path):
    orig_path = path

    if hasattr(torrent_file, 'seek') and hasattr(torrent_file, 'read'):
        torrent_file.seek(0)
        torrent = bdecode(torrent_file.read())
    else:
        try:
            with open(torrent_file, 'rb') as f:
                torrent = bdecode(f.read())
        except (IOError, TypeError):
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
    piece_hashes = _chunks(piece_hashes, 20)

    try:
        filenames = ['/'.join([y.decode('utf-8') for y in x[b'path']])
                     for x in torrent[b'info'][b'files']]
    except KeyError as e:
        if e.args[0] != b'files':
            raise e

        # Single file torrent, never has a directory
        filenames = [path]
        path = orig_path

    pieces = _get_torrent_pieces(filenames, path, piece_length)

    for known_hash, piece in zip(piece_hashes, pieces):
        try:
            file_hash = sha1(piece).digest()
        except TypeError:
            raise VerificationError('Unable to get hash for piece')

        if not compare_digest(bytes(known_hash), file_hash):
            raise VerificationError('Computed hash does not match torrent file\'s hash')
