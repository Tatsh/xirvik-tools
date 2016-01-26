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

        if isdir(name):
            continue

        if size <= piece_length:
            with open(name, 'rb') as f:
                tmp = f.read()
                p_delta -= len(tmp)
                buf += tmp

            continue

        with open(name, 'rb') as f:
            while True:
                tmp = f.read(p_delta)
                p_delta -= len(tmp)

                if not tmp:
                    break

                if len(tmp) < p_delta:
                    buf += tmp
                    break

                buf += tmp

                if p_delta <= 0:
                    yield buf
                    buf = b''
                    p_delta = piece_length


def verify_torrent_contents(torrent_file, path):
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

    if not isdir(path):
        return False

    piece_length = torrent[b'info'][b'piece length']
    piece_hashes = torrent[b'info'][b'pieces']
    piece_hashes = struct.unpack('<{}B'.format(len(piece_hashes)),
                                 piece_hashes)
    piece_hashes = _chunks(piece_hashes, 20)
    filenames = [x[b'path'][0].decode('utf-8')
                 for x in torrent[b'info'][b'files']]

    pieces = _get_torrent_pieces(filenames, path, piece_length)

    for known_hash, piece in zip(piece_hashes, pieces):
        try:
            file_hash = sha1(piece).digest()
        except TypeError:
            return False

        if not compare_digest(bytes(known_hash), file_hash):
            return False

    return True
