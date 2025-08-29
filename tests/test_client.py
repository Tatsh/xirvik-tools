"""Client tests."""
from __future__ import annotations

from os import environ
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import TYPE_CHECKING, Any, cast
import xmlrpc.client

from requests.exceptions import HTTPError
from xirvik.client import ListTorrentsError, UnexpectedruTorrentError, log, ruTorrentClient
from xirvik.typing import FileDownloadStrategy, FilePriority
from xirvik.utils import parse_header
import pytest

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture
    import requests_mock as req_mock


def test_netrc() -> None:
    with NamedTemporaryFile('w', encoding='utf-8') as f:
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
        path_d = Path(d)
        with (path_d / '.netrc').open('w') as f:
            f.write('machine hostname-test.com login a password b')
        client = ruTorrentClient('hostname-test.com')
        assert client.host == 'hostname-test.com'


def test_http_prefix() -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    assert client.http_prefix == 'https://hostname-test.com'


def test_add_torrent_bad_status(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    with NamedTemporaryFile('w', encoding='utf-8') as f:
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
    requests_mock.post(client.multirpc_action_uri, json={'t': []})
    with pytest.raises(ListTorrentsError):
        list(client.list_torrents())


def test_list_torrents(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    requests_mock.post(client.multirpc_action_uri,
                       json={
                           't': {
                               'hash here': [
                                   '1', '0', '1', '1', 'name of torrent?', '1000', '1', '1024',
                                   '1000', '0', '0.14', '0', '0', '512', 'label'
                               ] + (20 * ['0']) + ['1633423132\n'],
                           },
                           'cid': 92385,
                       })
    assert next(iter(client.list_torrents())).name == 'name of torrent?'


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
    assert files[0][4] == FilePriority.NORMAL
    assert files[0][5] == FileDownloadStrategy.NORMAL


def test_list_all_files(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    requests_mock.register_uri('POST', client.multirpc_action_uri, [{
        'json': {
            't': {
                'hash here': [
                    '1', '0', '1', '1', 'name of torrent?', '1000', '1', '1024', '1000', '0',
                    '0.14', '0', '0', '512', 'label'
                ] + (20 * ['0']) + ['1633423132\n'],
            },
            'cid': 92385,
        }
    }, {
        'json': [['name of file', '14', '13', '8192', '1', '0', '0'] + (19 * ['0'])]
    }])
    files = list(client.list_all_files())
    assert files[0][0] == 'name of file'
    assert files[0][1] == 14
    assert files[0][2] == 13
    assert files[0][3] == 8192
    assert files[0][4] == FilePriority.NORMAL
    assert files[0][5] == FileDownloadStrategy.NORMAL


def test_set_label_to_hashes_bad_args() -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    with pytest.raises(TypeError):
        client.set_label_to_hashes()


def test_set_label_to_hashes_normal(mocker: MockerFixture, requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    spy_log_warning = mocker.spy(log, 'warning')
    requests_mock.post(client.multirpc_action_uri, json=[{}])
    client.set_label_to_hashes(hashes=['hash1'], label='new label', allow_recursive_fix=False)
    assert spy_log_warning.call_count == 0


def test_set_label_to_hashes_recursion_limit_5(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    hashes = ['hash1', 'hash2']
    label = 'my new label'
    list_torrents_json = {
        't': {
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
        'cid': 92983,
    }
    responses = cast('list[dict[str, Any]]', [{
        'json': []
    }, {
        'json': list_torrents_json
    }, {
        'json': []
    }, {
        'json': list_torrents_json
    }, {
        'json': []
    }, {
        'json': list_torrents_json
    }, {
        'json': []
    }, {
        'json': list_torrents_json
    }, {
        'json': []
    }, {
        'json': list_torrents_json
    }, {
        'json': []
    }])
    requests_mock.post(client.multirpc_action_uri, responses)
    client.set_label_to_hashes(hashes=hashes, label=label, recursion_limit=5)


def test_set_label(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    list_torrents_json = {
        't': {
            'hash1': [
                '1', '0', '1', '1', 'torrent name', '250952849', '958', '958', '250952849',
                '357999402', '1426', '0', '0', '262144', 'a label'
            ] + (20 * ['0']) + ['1633423132\n']
        },
        'cid': 92983,
    }
    responses = cast('list[dict[str, Any]]', [
        {
            'json': []
        },
        {
            'json': list_torrents_json
        },
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
    requests_mock.post(client.datadir_action_uri, json={})
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
    mc.return_value.return_value.results = [{'faultCode': '2000', 'faultString': 'some string'}]
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


def test_parse_header_quotes() -> None:
    res = parse_header(r'something/blah; def=123; abc="abc\"de\"";')
    assert res[0] == 'something/blah'
    assert isinstance(res[1], dict)
    assert len(res[1].keys()) == 2
    assert res[1]['def'] == '123'
    assert res[1]['abc'] == 'abc"de"'


def test_parse_header_bad_quotes() -> None:
    res = parse_header(r'something/blah; bad="123; good=234;')
    assert res[0] == 'something/blah'
    assert isinstance(res[1], dict)
    assert len(res[1].keys()) == 1
    assert res[1]['bad'] == '"123; good=234;'


def test_parse_header() -> None:
    res = parse_header('something/blah')
    assert res[0] == 'something/blah'
    assert isinstance(res[1], dict)
    assert len(res[1].keys()) == 0


def test_edit_torrent(requests_mock: req_mock.Mocker) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    z = requests_mock.post(f'{client.http_prefix}/rtorrent/plugins/edit/action.php')
    r = client.edit_torrents(['hash1', 'hash2'],
                             comment='New comment',
                             private=True,
                             trackers=['http://tracker.example.com', 'http://tracker2.example.com'])
    assert r.status_code == 200
    # cspell: disable  # noqa: ERA001
    assert z.request_history[0].text == (
        'comment=New+comment&set_comment=1&private=1&set_private=1&set_trackers=1&hash=hash1'
        '&hash=hash2&tracker=http%3A%2F%2Ftracker.example.com&'
        'tracker=http%3A%2F%2Ftracker2.example.com')
    # cspell: enable  # noqa: ERA001
