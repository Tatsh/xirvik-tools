from os import close as close_fd, remove as rm, write as write_fd
from tempfile import mkstemp
from urllib.parse import quote
import unittest

from requests.exceptions import HTTPError
import requests_mock

from xirvik.client import (
    ruTorrentClient,
    TORRENT_FILE_PRIORITY_NORMAL,
    TORRENT_FILE_DOWNLOAD_STRATEGY_NORMAL,
)


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
        netrc_line = ('machine hostname-test.com login a password '
                      'bbbb\n').encode('utf-8')
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

        m.post(client._add_torrent_uri, status_code=400)
        with self.assertRaises(HTTPError):
            client.add_torrent(torrent)

    @requests_mock.Mocker()
    def test_list_torrents_bad_status(self, m):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.post(client.multirpc_action_uri, status_code=400)

        with self.assertRaises(HTTPError):
            client.list_torrents()

    @requests_mock.Mocker()
    def test_list_torrents(self, m):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.post(client.multirpc_action_uri, json=dict(
            t={
                'hash here': ['1', '0', '1', '1', 'name of torrent?'],
            },
            cid=92385,
        ))

        self.assertEqual(client.list_torrents()['hash here'][4],
                         'name of torrent?')

    @requests_mock.Mocker()
    def test_get_torrent(self, m):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        uri = ('{}/rtorrent/plugins/source/action.php'
               '?hash=hash_of_torrent').format(client.http_prefix)
        m.get(uri, headers={'content-disposition': 'attachment; '
                            'filename=test.torrent'})
        _, fn = client.get_torrent('hash_of_torrent')

        self.assertEqual('test.torrent', fn)

    @requests_mock.Mocker()
    def test_list_files(self, m):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        hash = 'testhash'

        cmds = (quote('f.prioritize_first='), quote('f.prioritize_last='),)
        query = 'mode=fls&hash={}'.format(hash).encode('utf-8')
        cmds = '&'.join(['cmd={}'.format(x) for x in cmds])
        query += b'&'
        query += cmds.encode('utf-8')
        m.post(client.multirpc_action_uri, json=[
            ['name of file', '14', '13', '8192', '1', '0', '0'],
        ])

        files = list(client.list_files('testhash'))
        self.assertEqual('name of file', files[0][0])
        self.assertEqual(14, files[0][1])
        self.assertEqual(13, files[0][2])
        self.assertNotEqual('8192', files[0][3])
        self.assertEqual(8192, files[0][3])
        self.assertEqual(TORRENT_FILE_PRIORITY_NORMAL, files[0][4])
        self.assertEqual(TORRENT_FILE_DOWNLOAD_STRATEGY_NORMAL, files[0][5])


if __name__ == '__main__':
    unittest.main()
