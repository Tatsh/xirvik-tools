"""Client tests."""
from os import environ
from os.path import join as path_join
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, cast
import xmlrpc.client

from pytest_mock.plugin import MockerFixture
from requests.exceptions import HTTPError
import pytest
import requests_mock as req_mock

from xirvik.client import ListTorrentsError, UnexpectedruTorrentError, ruTorrentClient
from xirvik.typing import FileDownloadStrategy, FilePriority

# pylint: disable=missing-function-docstring,protected-access,unused-variable


def test_netrc() -> None:
    with NamedTemporaryFile('w') as f:
        f.write('machine hostname-test.com login a password bbbb\n')
        f.flush()
        client = ruTorrentClient('hostname-test.com', netrc_path=f.name)
        assert client.name == 'a'
        assert client.password == 'bbbb'
        assert client.host == 'hostname-test.com'
        assert client.auth[0] == 'a'
        assert client.auth[1] == 'bbbb'


def test_no_netrc_path() -> None:
    with TemporaryDirectory() as d:
        environ['HOME'] = d
        with open(path_join(d, '.netrc'), 'w') as f:
            f.write('machine hostname-test.com login a password b')
        client = ruTorrentClient('hostname-test.com')
        assert client.host == 'hostname-test.com'


def test_http_prefix() -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    assert client.http_prefix == 'https://hostname-test.com'


def test_add_torrent_bad_status(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    with NamedTemporaryFile('w') as f:
        requests_mock.post(client.add_torrent_uri, status_code=400)
        with pytest.raises(HTTPError):
            client.add_torrent(f.name)


def test_list_torrents_bad_status(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    requests_mock.post(client.multirpc_action_uri, status_code=400)
    with pytest.raises(HTTPError):
        list(client.list_torrents())


def test_list_torrents_bad_type(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    requests_mock.post(client.multirpc_action_uri, json=dict(t=[]))
    with pytest.raises(ListTorrentsError):
        list(client.list_torrents())


def test_list_torrents(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    requests_mock.post(client.multirpc_action_uri,
                       json=dict(
                           t={
                               'hash here': [
                                   '1', '0', '1', '1', 'name of torrent?', '1000', '1', '1024',
                                   '1000', '0', '0.14', '0', '0', '512', 'label'
                               ] + (20 * ['0']) + ['1633423132\n'],
                           },
                           cid=92385,
                       ))
    assert list(client.list_torrents())[0].name == 'name of torrent?'


def test_get_torrent(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    uri = (f'{client.http_prefix}/rtorrent/plugins/source/action.php'
           '?hash=hash_of_torrent')
    requests_mock.get(uri, headers={'content-disposition': 'attachment; '
                                                           'filename=test.torrent'})
    _, fn = client.get_torrent('hash_of_torrent')

    assert fn == 'test.torrent'


def test_list_files(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')

    requests_mock.post(client.multirpc_action_uri,
                       json=[
                           ['name of file', '14', '13', '8192', '1', '0', '0'] + (19 * ['0']),
                       ])

    files = list(client.list_files('test_hash'))
    assert files[0][0] == 'name of file'
    assert files[0][1] == 14
    assert files[0][2] == 13
    assert files[0][3] == 8192
    assert FilePriority.NORMAL == files[0][4]
    assert FileDownloadStrategy.NORMAL == files[0][5]


def test_set_label_to_hashes_bad_args() -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    with pytest.raises(TypeError):
        client.set_label_to_hashes()


def test_set_label_to_hashes_normal(mocker: MockerFixture, requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    spy_log_warning = mocker.spy(client._log, 'warning')
    requests_mock.post(client.multirpc_action_uri, json=[{}])
    client.set_label_to_hashes(hashes=['hash1'], label='new label', allow_recursive_fix=False)
    assert spy_log_warning.call_count == 0


def test_set_label_to_hashes_recursion_limit_5(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    hashes = ['hash1', 'hash2']
    label = 'my new label'
    list_torrents_json = dict(
        t={
            'hash1': [
                '1', '0', '1', '1', 'torrent name', '250952849', '958', '958', '250952849',
                '357999402', '1426', '0', '0', '262144', ''
            ] + (20 * ['0']) + ['1633423132\n'],
            'hash2': [
                '1', '0', '1', '1', 'torrent name2', '250952849', '958', '958', '250952849',
                '357999402', '1426', '0', '0', '262144', ''
            ] + (20 * ['0']) + ['1633423132\n'],
            'hash3': [
                '1', '0', '1', '1', 'torrent name2', '250952849', '958', '958', '250952849',
                '357999402', '1426', '0', '0', '262144', ''
            ] + (20 * ['0']) + ['1633423132\n'],
        },
        cid=92983,
    )
    responses = cast(list[dict[str, Any]], [
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
    requests_mock.post(client.multirpc_action_uri, responses)
    client.set_label_to_hashes(hashes=hashes, label=label, recursion_limit=5)


def test_set_label(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    list_torrents_json = dict(
        t=dict(hash1=[
            '1', '0', '1', '1', 'torrent name', '250952849', '958', '958', '250952849', '357999402',
            '1426', '0', '0', '262144', 'a label'
        ] + (20 * ['0']) + ['1633423132\n']),
        cid=92983,
    )
    responses = cast(list[dict[str, Any]], [
        dict(json=[]),
        dict(json=list_torrents_json),
    ])

    requests_mock.post(client.multirpc_action_uri, responses)
    client.set_label('hash1', 'a label')


def test_move_torrent(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')

    requests_mock.post(client.datadir_action_uri, json=[], status_code=400)
    with pytest.raises(HTTPError):
        client.move_torrent('hash1', 'new_place')

    requests_mock.post(client.datadir_action_uri, json={'errors': ['some error']})
    with pytest.raises(UnexpectedruTorrentError):
        client.move_torrent('hash1', 'new_place')


def test_move_torrent_no_errors(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    requests_mock.post(client.datadir_action_uri, json=[])
    try:
        client.move_torrent('hash1', 'new_place')
    except UnexpectedruTorrentError:  # pragma no cover
        pytest.fail('Unexpected ruTorrent error exception')


def test_remove(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    requests_mock.post(client.multirpc_action_uri, json=[], status_code=400)
    with pytest.raises(HTTPError):
        client.remove('some hash')


def test_stop(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    requests_mock.post(client.multirpc_action_uri, json=[], status_code=400)
    with pytest.raises(HTTPError):
        client.stop('some hash')


def test_add_torrent_url(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    requests_mock.post(client.add_torrent_uri, json=[], status_code=400)
    with pytest.raises(HTTPError):
        client.add_torrent_url('https://some-url')


def test_delete(mocker: MockerFixture) -> None:
    mc = mocker.patch('xirvik.client.xmlrpc.MultiCall')
    mc.return_value.return_value.results = [dict(faultCode='2000', faultString='some string')]
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    with pytest.raises(xmlrpc.client.Fault):
        client.delete('some hash')


def test_delete2(mocker: MockerFixture) -> None:
    mc = mocker.patch('xirvik.client.xmlrpc.MultiCall')
    mc.return_value.return_value.results = [{}]
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    try:
        client.delete('some hash')
    except xmlrpc.client.Fault:  # pragma no cover
        pytest.fail('Unexpected fault')
