"""Client tests."""
from datetime import datetime
from os import close as close_fd, environ, remove as rm, write as write_fd
from os.path import join as path_join
from tempfile import mkstemp, TemporaryDirectory
from typing import Any, Dict, List, Optional, cast
import unittest

from requests.exceptions import HTTPError
import requests_mock

from xirvik.client import (TORRENT_FILE_DOWNLOAD_STRATEGY_NORMAL,
                           TORRENT_FILE_PRIORITY_NORMAL,
                           UnexpectedruTorrentError, ruTorrentClient)

# pylint: disable=missing-function-docstring,missing-class-docstring,protected-access,no-self-use


def isfile(filepath: str) -> bool:
    try:
        with open(filepath, 'rb'):
            return True
    except IOError:
        pass

    return False


class TestRuTorrentClient(unittest.TestCase):
    _temp_files: List[str] = []

    def tearDown(self):
        for x in self._temp_files:
            try:
                rm(x)
            except OSError:
                pass

    def _mktemp(self,
                contents: Optional[bytes] = None,
                prefix: str = 'test-rutorrent-client-'):
        fd, name = mkstemp(prefix=prefix)
        write_fd(fd, contents or b'')
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

    def test_no_netrc_path(self):
        with TemporaryDirectory() as d:
            environ['HOME'] = d
            with open(path_join(d, '.netrc'), 'w') as f:
                f.write('machine hostname-test.com login a password b')
            client = ruTorrentClient('hostname-test.com')
            self.assertEqual('hostname-test.com', client.host)

    def test_http_prefix(self):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        self.assertEqual('https://hostname-test.com', client.http_prefix)

    @requests_mock.Mocker()
    def test_add_torrent_bad_status(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        torrent = self._mktemp('torrent file fake'.encode('utf-8'))

        m.post(client._add_torrent_uri, status_code=400)
        with self.assertRaises(HTTPError):
            client.add_torrent(torrent)

    @requests_mock.Mocker()
    def test_list_torrents_bad_status(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.post(client.multirpc_action_uri, status_code=400)

        with self.assertRaises(HTTPError):
            client.list_torrents()

    @requests_mock.Mocker()
    def test_list_torrents_bad_type(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.post(client.multirpc_action_uri, json=dict(t=[]))
        with self.assertRaises(ValueError):
            client.list_torrents()

    @requests_mock.Mocker()
    def test_list_torrents(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.post(client.multirpc_action_uri,
               json=dict(
                   t={
                       'hash here': ['1', '0', '1', '1', 'name of torrent?'],
                   },
                   cid=92385,
               ))

        self.assertEqual(client.list_torrents()['hash here'][4],
                         'name of torrent?')

    @requests_mock.Mocker()
    def test_list_torrents_dict(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.post(
            client.multirpc_action_uri,
            json=dict(
                t={
                    'hash here': [
                        '1',  # is_open
                        '0',  # is_hash_checking
                        '1',  # is_hash_checked
                        '1',  # state
                        'name of torrent?',  # name
                        '100',  # size_bytes
                        '1',  # completed_chunks
                        '1',  # size_chunks
                        '100',  # bytes_done
                        '0',  # up_total
                        '0',  # ratio,
                        '0',  # up_rate
                        '0',  # down_rate
                        '256',  # chunk_size
                        'label',  # custom1
                        '0',  # peers_accounted
                        '0',  # peers_not_connected
                        '0',  # peers_connected
                        '0',  # peers_complete
                        '0',  # left_bytes
                        '0',  # priority
                        '1631205742',  # state_changed
                        '0',  # skip_total
                        '0',  # hashing
                        '1',  # chunks_hashed
                        '/path',  # base_path
                        '1631205742',  # creation_date
                        '0',  # tracker_focus
                        '1',  # is_active
                        'some message',  # message
                        'unknown field',  # custom2
                        '1',  # free_diskspace
                        '1',  # is_private
                        '0',  # is_multi_file
                        'junk',  # junk, ignored
                    ],
                },
                cid=92385,
            ))
        d = list(client.list_torrents_dict().values())[0]
        self.assertIsInstance(d['state_changed'], datetime)
        self.assertIsInstance(d['creation_date'], datetime)
        self.assertEqual(True, d['is_open'])
        self.assertEqual(False, d['is_hash_checking'])
        self.assertEqual('name of torrent?', d['name'])
        self.assertNotIn('junk', d.values())

    @requests_mock.Mocker()
    def test_list_torrents_dict_bad_values(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        m.post(
            client.multirpc_action_uri,
            json=dict(
                t={
                    'hash here': [
                        '1',  # is_open
                        '0',  # is_hash_checking
                        '1',  # is_hash_checked
                        '1',  # state
                        'name of torrent?',  # name
                        '100',  # size_bytes
                        '1',  # completed_chunks
                        '1',  # size_chunks
                        '100',  # bytes_done
                        '0',  # up_total
                        '0',  # ratio,
                        '0',  # up_rate
                        '0',  # down_rate
                        '256',  # chunk_size
                        'label',  # custom1
                        '0',  # peers_accounted
                        '0',  # peers_not_connected
                        '0',  # peers_connected
                        '0',  # peers_complete
                        '0',  # left_bytes
                        '0',  # priority
                        '1631205742',  # state_changed
                        '0',  # skip_total
                        '0',  # hashing
                        '1',  # chunks_hashed
                        '/path',  # base_path
                        '1631205742aaaa',  # creation_date
                        '0',  # tracker_focus
                        '1',  # is_active
                        'some message',  # message
                        'unknown field',  # custom2
                        '1.0.',  # free_diskspace
                        '1',  # is_private
                        '0',  # is_multi_file
                    ],
                },
                cid=92385,
            ))
        d = list(client.list_torrents_dict().values())[0]
        self.assertIsNone(d['creation_date'])
        self.assertIsNone(d['free_diskspace'])

    @requests_mock.Mocker()
    def test_get_torrent(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        uri = (f'{client.http_prefix}/rtorrent/plugins/source/action.php'
               '?hash=hash_of_torrent')
        m.get(uri,
              headers={
                  'content-disposition': 'attachment; '
                  'filename=test.torrent'
              })
        _, fn = client.get_torrent('hash_of_torrent')

        self.assertEqual('test.torrent', fn)

    @requests_mock.Mocker()
    def test_list_files(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')

        m.post(client.multirpc_action_uri,
               json=[
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

    @requests_mock.Mocker()
    def test_set_label_to_hashes_recursion_limit_5(self,
                                                   m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        hashes = ['hash1', 'hash2']
        label = 'my new label'
        list_torrents_json = dict(
            t={
                'hash1': [
                    '1', '0', '1', '1', 'torrent name', '250952849', '958',
                    '958', '250952849', '357999402', '1426', '0', '0',
                    '262144', ''
                ],
                'hash2': [
                    '1', '0', '1', '1', 'torrent name2', '250952849', '958',
                    '958', '250952849', '357999402', '1426', '0', '0',
                    '262144', ''
                ],
            },
            cid=92983,
        )
        responses = cast(List[Dict[str, Any]], [
            dict(json=[]),
            dict(json=list_torrents_json),
            dict(json=[]),
            dict(json=list_torrents_json),
            dict(json=[]),
            dict(json=list_torrents_json),
            dict(json=[]),
            dict(json=list_torrents_json),
            dict(json=[]),
            dict(json=list_torrents_json),
            dict(json=[]),
        ])

        m.post(client.multirpc_action_uri, responses)
        client.set_label_to_hashes(hashes=hashes,
                                   label=label,
                                   recursion_limit=5)

        with self.assertRaises(TypeError):
            client.set_label_to_hashes()

    @requests_mock.Mocker()
    def test_set_label(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')
        list_torrents_json = dict(
            t=dict(hash1=[
                '1', '0', '1', '1', 'torrent name', '250952849', '958', '958',
                '250952849', '357999402', '1426', '0', '0', '262144', 'a label'
            ],),
            cid=92983,
        )
        responses = cast(List[Dict[str, Any]], [
            dict(json=[]),
            dict(json=list_torrents_json),
        ])

        m.post(client.multirpc_action_uri, responses)
        client.set_label('hash1', 'a label')

    @requests_mock.Mocker()
    def test_move_torrent(self, m: requests_mock.Mocker):
        client = ruTorrentClient('hostname-test.com', 'a', 'b')

        m.post(client.datadir_action_uri, json=[], status_code=400)
        with self.assertRaises(HTTPError):
            client.move_torrent('hash1', 'newplace')

        m.post(client.datadir_action_uri, json={'errors': ['some error']})
        with self.assertRaises(UnexpectedruTorrentError):
            client.move_torrent('hash1', 'newplace')


if __name__ == '__main__':
    unittest.main()
