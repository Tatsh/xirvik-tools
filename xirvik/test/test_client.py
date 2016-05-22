from os import close as close_fd, remove as rm, write as write_fd
from tempfile import mkstemp
import unittest

from requests.exceptions import HTTPError
import requests_mock

from xirvik.client import ruTorrentClient


def isfile(filepath):
    try:
        with open(filepath, 'rb'):
            return True
    except IOError:
        pass

    return False


class TestRuTorrentClient(unittest.TestCase):
    _temp_files = []

    def tearDown(self):
        for x in self._temp_files:
            try:
                rm(x)
            except IOError:
                pass

    def _mktemp(self, contents=None, prefix='test-rutorrent-client-'):
        fd, name = mkstemp(prefix=prefix)
        write_fd(fd, contents)
        close_fd(fd)

        self._temp_files.append(name)

        return name

    def test_netrc(self):
        netrc_line = 'machine hostname-test.com login a password bbbb\n'.encode('utf-8')
        name = self._mktemp(contents=netrc_line)

        client = ruTorrentClient('hostname-test.com', netrc_path=name)
        self.assertEqual('a', client.name)
        self.assertEqual('bbbb', client.password)
        self.assertEqual('hostname-test.com', client.host)

        self.assertEqual('a', client.auth[0])
        self.assertEqual('bbbb', client.auth[1])

    def test_http_prefix(self):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        self.assertEqual('https://hostname-test.com', client.http_prefix)

    @requests_mock.Mocker()
    def test_add_torrent_bad_status(self, m):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        torrent = self._mktemp('torrent file fake'.encode('utf-8'))

        m.post('https://hostname-test.com/rtorrent/php/addtorrent.php', status_code=400)
        with self.assertRaises(HTTPError):
            client.add_torrent(torrent)

    @requests_mock.Mocker()
    def test_list_torrents_bad_status(self, m):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.post('https://hostname-test.com/rtorrent/plugins/multirpc/action.php', status_code=400)

        with self.assertRaises(HTTPError):
            client.list_torrents()

    @requests_mock.Mocker()
    def test_list_torrents(self, m):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.post('https://hostname-test.com/rtorrent/plugins/multirpc/action.php', json=dict(
            t={
                'hash here': ['1', '0', '1', '1', 'name of torrent?'],
            },
            cid=92385,
        ))

        self.assertEqual(client.list_torrents()['hash here'][4], 'name of torrent?')

    @requests_mock.Mocker()
    def test_get_torrent(self, m):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.get('https://hostname-test.com/rtorrent/plugins/source/action.php?hash=hash_of_torrent', headers={
            'content-disposition': 'attachment; filename=test.torrent',
        })
        _, fn = client.get_torrent('hash_of_torrent')

        self.assertEqual('test.torrent', fn)


if __name__ == '__main__':
    unittest.main()
