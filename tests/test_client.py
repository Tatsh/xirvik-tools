"""Client tests."""
from __future__ import annotations

from os import environ
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import TYPE_CHECKING, Any, cast
import xmlrpc.client

from niquests.exceptions import HTTPError
from niquests_mock import MockRouter, build_response
from tests.conftest import alist
from xirvik.client import ListTorrentsError, UnexpectedruTorrentError, log, ruTorrentClient
from xirvik.typing import FileDownloadStrategy, FilePriority
from xirvik.utils import parse_header
import pytest

if TYPE_CHECKING:
    from niquests.models import PreparedRequest, Response
    from pytest_mock.plugin import MockerFixture


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


def test_netrc_no_entry() -> None:
    with NamedTemporaryFile('w', encoding='utf-8') as f:
        f.write('machine other-host.com login a password b\n')
        f.flush()
        with pytest.raises(ValueError, match=r'No netrc entry found for hostname-test\.com'):
            ruTorrentClient('hostname-test.com', netrc_path=f.name)


def test_name_required() -> None:
    with pytest.raises(ValueError, match='Username is required'):
        ruTorrentClient('hostname-test.com', password='bbbb')


def test_password_required() -> None:
    with pytest.raises(ValueError, match='Password is required'):
        ruTorrentClient('hostname-test.com', name='a')


def test_http_prefix() -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    assert client.http_prefix == 'https://hostname-test.com'


async def test_add_torrent_bad_status(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    with NamedTemporaryFile('w', encoding='utf-8') as f:
        niquests_mock.post(client.add_torrent_uri).respond(400)
        with pytest.raises(HTTPError):
            await client.add_torrent(f.name)


async def test_list_torrents_bad_status(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    niquests_mock.post(client.multirpc_action_uri).respond(400)
    with pytest.raises(HTTPError):
        await alist(client.list_torrents())


async def test_list_torrents_bad_type(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    niquests_mock.post(client.multirpc_action_uri).respond(json={'t': []})
    with pytest.raises(ListTorrentsError):
        await alist(client.list_torrents())


async def test_list_torrents(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    niquests_mock.post(client.multirpc_action_uri).respond(
        json={
            't': {
                'hash here': [
                    '1', '0', '1', '1', 'name of torrent?', '1000', '1', '1024', '1000', '0',
                    '0.14', '0', '0', '512', 'label'
                ] + (20 * ['0']) + ['1633423132\n'],
            },
            'cid': 92385,
        })
    result = await alist(client.list_torrents())
    assert result[0].name == 'name of torrent?'


async def test_get_torrent(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    uri = (f'{client.http_prefix}/rtorrent/plugins/source/action.php'
           '?hash=hash_of_torrent')
    niquests_mock.get(uri).respond(
        headers={'content-disposition': 'attachment; '
                                        'filename=test.torrent'})
    _, fn = await client.get_torrent('hash_of_torrent')
    assert fn == 'test.torrent'


async def test_list_files(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    niquests_mock.post(client.multirpc_action_uri).respond(
        json=[['name of file', '14', '13', '8192', '1', '0', '0'] + (19 * ['0'])])
    files = await alist(client.list_files('test_hash'))
    assert files[0][0] == 'name of file'
    assert files[0][1] == 14
    assert files[0][2] == 13
    assert files[0][3] == 8192
    assert files[0][4] == FilePriority.NORMAL
    assert files[0][5] == FileDownloadStrategy.NORMAL


async def test_list_all_files(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    call_count = 0
    list_torrents_json: dict[str, Any] = {
        't': {
            'hash here': [
                '1', '0', '1', '1', 'name of torrent?', '1000', '1', '1024', '1000', '0', '0.14',
                '0', '0', '512', 'label'
            ] + (20 * ['0']) + ['1633423132\n'],
        },
        'cid': 92385,
    }
    list_files_json = [['name of file', '14', '13', '8192', '1', '0', '0'] + (19 * ['0'])]
    responses: list[dict[str, Any]] = [{'json': list_torrents_json}, {'json': list_files_json}]

    def side_effect(request: PreparedRequest) -> Response:
        nonlocal call_count
        resp = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return build_response(request, **resp)

    niquests_mock.post(client.multirpc_action_uri).mock(side_effect=side_effect)
    files = await alist(client.list_all_files())
    assert files[0][0] == 'name of file'
    assert files[0][1] == 14
    assert files[0][2] == 13
    assert files[0][3] == 8192
    assert files[0][4] == FilePriority.NORMAL
    assert files[0][5] == FileDownloadStrategy.NORMAL


async def test_set_label_to_hashes_bad_args() -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    with pytest.raises(TypeError):
        await client.set_label_to_hashes()


async def test_set_label_to_hashes_normal(mocker: MockerFixture, niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    spy_log_warning = mocker.spy(log, 'warning')
    niquests_mock.post(client.multirpc_action_uri).respond(json=[{}])
    await client.set_label_to_hashes(hashes=['hash1'], label='new label', allow_recursive_fix=False)
    assert spy_log_warning.call_count == 0


async def test_set_label_to_hashes_recursion_limit_5(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    hashes = ['hash1', 'hash2']
    label = 'my new label'
    list_torrents_json: dict[str, Any] = {
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
    response_sequence = cast('list[dict[str, Any]]', [{
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
    call_count = 0

    def side_effect(request: PreparedRequest) -> Response:
        nonlocal call_count
        resp = response_sequence[min(call_count, len(response_sequence) - 1)]
        call_count += 1
        return build_response(request, **resp)

    niquests_mock.post(client.multirpc_action_uri).mock(side_effect=side_effect)
    await client.set_label_to_hashes(hashes=hashes, label=label, recursion_limit=5)


async def test_set_label(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    list_torrents_json: dict[str, Any] = {
        't': {
            'hash1': [
                '1', '0', '1', '1', 'torrent name', '250952849', '958', '958', '250952849',
                '357999402', '1426', '0', '0', '262144', 'a label'
            ] + (20 * ['0']) + ['1633423132\n']
        },
        'cid': 92983,
    }
    response_sequence = cast('list[dict[str, Any]]', [
        {
            'json': []
        },
        {
            'json': list_torrents_json
        },
    ])
    call_count = 0

    def side_effect(request: PreparedRequest) -> Response:
        nonlocal call_count
        resp = response_sequence[min(call_count, len(response_sequence) - 1)]
        call_count += 1
        return build_response(request, **resp)

    niquests_mock.post(client.multirpc_action_uri).mock(side_effect=side_effect)
    await client.set_label('hash1', 'a label')


async def test_move_torrent(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    call_count = 0

    def side_effect(request: PreparedRequest) -> Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return build_response(request, status_code=400, json=[])
        return build_response(request, json={'errors': ['some error']})

    niquests_mock.post(client.datadir_action_uri).mock(side_effect=side_effect)
    with pytest.raises(HTTPError):
        await client.move_torrent('hash1', 'new_place')
    with pytest.raises(UnexpectedruTorrentError):
        await client.move_torrent('hash1', 'new_place')


async def test_move_torrent_no_errors(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    niquests_mock.post(client.datadir_action_uri).respond(json={})
    try:
        await client.move_torrent('hash1', 'new_place')
    except UnexpectedruTorrentError:  # pragma no cover
        pytest.fail('Unexpected ruTorrent error exception')


async def test_remove(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    niquests_mock.post(client.multirpc_action_uri).respond(400, json=[])
    with pytest.raises(HTTPError):
        await client.remove('some hash')


async def test_stop(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    niquests_mock.post(client.multirpc_action_uri).respond(400, json=[])
    with pytest.raises(HTTPError):
        await client.stop('some hash')


async def test_add_torrent_url(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    niquests_mock.post(client.add_torrent_uri).respond(400, json=[])
    with pytest.raises(HTTPError):
        await client.add_torrent_url('https://some-url')


async def test_delete(mocker: MockerFixture) -> None:
    mc = mocker.patch('xirvik.client.xmlrpc.MultiCall')
    mc.return_value.return_value.results = [{'faultCode': '2000', 'faultString': 'some string'}]
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    with pytest.raises(xmlrpc.client.Fault):
        await client.delete('some hash')


async def test_delete2(mocker: MockerFixture) -> None:
    mc = mocker.patch('xirvik.client.xmlrpc.MultiCall')
    mc.return_value.return_value.results = [{}]
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    try:
        await client.delete('some hash')
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


async def test_edit_torrent(niquests_mock: MockRouter) -> None:
    client = ruTorrentClient('hostname-test.com', 'a', 'b')
    route = niquests_mock.post(f'{client.http_prefix}/rtorrent/plugins/edit/action.php').respond()
    r = await client.edit_torrents(
        ['hash1', 'hash2'],
        comment='New comment',
        private=True,
        trackers=['http://tracker.example.com', 'http://tracker2.example.com'])
    assert r.status_code == 200
    assert route.call_count == 1
