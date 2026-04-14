"""Command line interface tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
from unittest.mock import AsyncMock
import json
import re

from tests.conftest import async_iter
from xirvik.commands.root import xirvik
from xirvik.typing import FileDownloadStrategy, FilePriority, TorrentTrackedFile

if TYPE_CHECKING:
    from click.testing import CliRunner
    from niquests_mock import MockRouter
    from pytest_mock.plugin import MockerFixture
    import pytest


def test_fix_rtorrent(niquests_mock: MockRouter, runner: CliRunner) -> None:
    niquests_mock.get('https://some_host.com:443/userpanel/index.php/services/'
                      'restart/rtorrent').respond()
    assert runner.invoke(xirvik, ('rtorrent', 'fix', '-H', 'some_host.com')).exit_code == 0


def test_fix_rtorrent_fail(niquests_mock: MockRouter, runner: CliRunner) -> None:
    niquests_mock.get('https://some_host.com:443/userpanel/index.php/services/'
                      'restart/rtorrent').respond(500)
    assert runner.invoke(xirvik, ('rtorrent', 'fix', '-H', 'some_host.com')).exit_code == 1


def test_start_torrents_zero_files(runner: CliRunner, tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    assert runner.invoke(xirvik,
                         ('rtorrent', 'add', '-H', 'machine.com', str(Path.home()))).exit_code == 0


def test_start_torrents_zero_torrent_files(runner: CliRunner, tmp_path: Path,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    non_torrent = tmp_path / 'a.not-a-torrent'
    non_torrent.write_bytes(b'\xFF')
    assert runner.invoke(xirvik,
                         ('rtorrent', 'add', '-H', 'machine.com', str(Path.home()))).exit_code == 0


def test_start_torrents_normal(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    torrent = tmp_path / 'a.torrent'
    torrent.write_bytes(b'\xFF')
    route = niquests_mock.post('https://machine.com:443/rtorrent/php/addtorrent.php?').respond()
    assert runner.invoke(xirvik,
                         ('rtorrent', 'add', '-H', 'machine.com', str(Path.home()))).exit_code == 0
    assert not torrent.is_file()
    assert route.call_count == 1


def test_start_torrents_error_uploading(runner: CliRunner, niquests_mock: MockRouter,
                                        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    torrent = tmp_path / 'a.torrent'
    torrent.write_bytes(b'\xFF')
    route = niquests_mock.post('https://machine.com:443/rtorrent/php/addtorrent.php?').respond(500)
    assert runner.invoke(xirvik,
                         ('rtorrent', 'add', '-H', 'machine.com', str(Path.home()))).exit_code == 0
    assert torrent.is_file()
    assert route.call_count == 1


def test_start_torrents_start_stopped(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                                      monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    torrent = tmp_path / 'a.torrent'
    torrent.write_text('')
    route = niquests_mock.post('https://machine.com:443/rtorrent/php/addtorrent.php?').respond()
    assert runner.invoke(xirvik, ('rtorrent', 'add', '--start-stopped', '-d', '-H', 'machine.com',
                                  str(Path.home()))).exit_code == 0
    assert route.call_count == 1
    assert not torrent.is_file()


def test_add_ftp_user(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                      monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    route = niquests_mock.post(
        'https://machine.com:443/userpanel/index.php/ftp_users/add_user').respond()
    assert runner.invoke(
        xirvik, ('ftp', 'add-user', '-H', 'machine.com', 'newuser', 'new_pass')).exit_code == 0
    assert route.call_count == 1


def test_add_ftp_user_error(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    route = niquests_mock.post(
        'https://machine.com:443/userpanel/index.php/ftp_users/add_user').respond(500)
    assert runner.invoke(
        xirvik, ('ftp', 'add-user', '-H', 'machine.com', 'newuser', 'new_pass')).exit_code != 0
    assert route.call_count == 1


def test_delete_ftp_user(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                         monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    route = niquests_mock.get('https://machine.com:443/userpanel/index.php/ftp_users/delete/'
                              'bmV3dXNlcg==').respond()  # cspell: disable-line
    assert runner.invoke(xirvik,
                         ('ftp', 'delete-user', '-H', 'machine.com', 'newuser')).exit_code == 0
    assert route.call_count == 1


def test_delete_ftp_user_error(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    route = niquests_mock.get('https://machine.com:443/userpanel/index.php/ftp_users/delete/'
                              'bmV3dXNlcg==').respond(500)  # cspell: disable-line
    assert runner.invoke(xirvik,
                         ('ftp', 'delete-user', '-H', 'machine.com', 'newuser')).exit_code != 0
    assert route.call_count == 1


def test_list_ftp_users(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                        monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    niquests_mock.get('https://machine.com:443/userpanel/index.php/ftp_users').respond(
        text="""<table>
    <tbody>
        <tr class="gradeX">
            <td>some_user</td>
            <td>Yes</td>
            <td>/some_dir</td>
            <td></td>
        </tr>
    </tbody>
</table>""")
    run = runner.invoke(xirvik, ('ftp', 'list-users', '-H', 'machine.com'))
    assert run.exit_code == 0
    assert 'some_user' in run.output
    assert '/some_dir' in run.output


def test_list_ftp_users_error(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                              monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    niquests_mock.get('https://machine.com:443/userpanel/index.php/ftp_users').respond(500)
    assert runner.invoke(xirvik, ('ftp', 'list-users', '-H', 'machine.com')).exit_code != 0


def test_authorize_ip(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                      monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    route = niquests_mock.get('https://machine.com:443/userpanel/index.php/virtual_machine/'
                              'authorize_ip').respond()
    assert runner.invoke(xirvik, ('vm', 'authorize-ip', '-H', 'machine.com')).exit_code == 0
    assert route.call_count == 1


def test_authorize_ip_error(runner: CliRunner, niquests_mock: MockRouter, tmp_path: Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    route = niquests_mock.get('https://machine.com:443/userpanel/index.php/virtual_machine/'
                              'authorize_ip').respond(500)
    assert runner.invoke(xirvik, ('vm', 'authorize-ip', '-H', 'machine.com')).exit_code != 0
    assert route.call_count == 1


class MinimalTorrentDict(NamedTuple):
    hash: str
    custom1: str | None = None
    left_bytes: int = 0
    name: str = ''
    ratio: float = 0
    creation_date: datetime | None = None
    state_changed: datetime | None = None
    is_hash_checking: bool = False
    base_path: str | None = None
    finished: datetime | None = None


def _patch_client_async(mocker: MockerFixture,
                        torrents: list[MinimalTorrentDict] | None = None,
                        files: list[TorrentTrackedFile] | None = None) -> AsyncMock:
    """Patch ruTorrentClient with async-compatible mocks."""
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    if torrents is not None:
        client_mock.return_value.list_torrents.return_value = async_iter(torrents)
    if files is not None:
        client_mock.return_value.list_files.return_value = async_iter(files)
    return client_mock


def test_list_torrents(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                       monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed')
                        ])
    lines = runner.invoke(xirvik, ('rtorrent', 'list-torrents')).output.splitlines()
    assert re.match(r'^Hash\s+Name\s+Label\s+Finished', lines[0])
    assert re.match(r'^hash1\s+The Name\s+TEST me', lines[1])


def test_list_torrents_json(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed')
                        ])
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '-F', 'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['name'] == 'The Name'


def test_list_torrents_json_reversed(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed'),
                            MinimalTorrentDict('hash2',
                                               custom1='TEST me',
                                               name='The Name2',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed')
                        ])
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '--reverse-order', '--table-format',
                               'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash2'
    assert data[1]['hash'] == 'hash1'


def test_list_torrents_json_sort_finished(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed',
                                               finished=datetime.now(timezone.utc)),
                            MinimalTorrentDict(
                                'hash2',
                                custom1='TEST me',
                                name='The Name2',
                                is_hash_checking=False,
                                base_path='/downloads/_completed',
                                finished=datetime.now(timezone.utc) - timedelta(days=7)),
                        ])
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '--sort', 'finished', '--table-format',
                               'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash2'
    assert data[1]['hash'] == 'hash1'


def test_list_torrents_json_sort_finished_missing(runner: CliRunner, mocker: MockerFixture,
                                                  tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed'),
                            MinimalTorrentDict(
                                'hash2',
                                custom1='TEST me',
                                name='The Name2',
                                is_hash_checking=False,
                                base_path='/downloads/_completed',
                                finished=datetime.now(timezone.utc) - timedelta(days=7)),
                        ])
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '--sort', 'finished', '--table-format',
                               'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash1'
    assert data[1]['hash'] == 'hash2'


def test_list_torrents_json_sort_missing_attr(runner: CliRunner, mocker: MockerFixture,
                                              tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict(
                                'hash1',
                                custom1='TEST me',
                                name='The Name',
                                is_hash_checking=False,
                                base_path='/downloads/_completed',
                                finished=datetime.now(timezone.utc) - timedelta(days=8)),
                            MinimalTorrentDict('hash2',
                                               name='The Name2',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed'),
                        ])
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '--sort', 'label', '--table-format',
                               'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash2'
    assert data[1]['hash'] == 'hash1'


def test_list_torrents_json_sort_other_criteria(runner: CliRunner, mocker: MockerFixture,
                                                tmp_path: Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed'),
                            MinimalTorrentDict('hash2',
                                               name='AThe Name2',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed'),
                        ])
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '--sort', 'name', '--table-format',
                               'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash2'
    assert data[1]['hash'] == 'hash1'


def test_list_files(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                    monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        files=[
                            TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL),
                            TorrentTrackedFile('file2', 512, 512, 1200, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL),
                        ])
    data = json.loads(
        runner.invoke(xirvik,
                      ('rtorrent', 'list-files', '--table-format', 'json', 'hash1')).output.strip())
    assert isinstance(data, list)
    assert data[0]['name'] == 'file1'
    assert data[1]['name'] == 'file2'


def test_list_files_reversed(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                             monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        files=[
                            TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL),
                            TorrentTrackedFile('file2', 512, 512, 1200, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL),
                        ])
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-files', '--reverse-order', '--table-format',
                               'json', 'hash1')).output.strip())
    assert isinstance(data, list)
    assert data[0]['name'] == 'file2'
    assert data[1]['name'] == 'file1'


def test_list_files_sort_size(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                              monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        files=[
                            TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL),
                            TorrentTrackedFile('file2', 512, 512, 1200, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL),
                        ])
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-files', '--table-format', 'json', '--sort',
                               'size_bytes', '--reverse-order', 'hash1')).output.strip())
    assert isinstance(data, list)
    assert data[0]['name'] == 'file2'
    assert data[1]['name'] == 'file1'


def test_list_files_normal(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                           monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        files=[
                            TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL),
                        ])
    lines = runner.invoke(xirvik, ('rtorrent', 'list-files', '--sort', 'size_bytes',
                                   '--reverse-order', 'hash1')).output.splitlines()
    assert re.match(r'^Name\s+Size\s+Downloaded Pieces\s+Number of Pieces\s+Priority ID', lines[0])
    assert re.match(r'file1\s+1000\s+512\s+512', lines[1])


def test_list_all_files_single(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed')
                        ],
                        files=[
                            TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL)
                        ])
    lines = runner.invoke(xirvik, ('rtorrent', 'list-all-files')).output.splitlines()
    assert re.match(r'^/downloads/_completed/file[0-9]$', lines[2])


def test_list_all_files_single_alt(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed/file1')
                        ],
                        files=[
                            TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL)
                        ])
    lines = runner.invoke(xirvik, ('rtorrent', 'list-all-files')).output.splitlines()
    assert re.match(r'^/downloads/_completed/file[0-9]$', lines[2])


def test_list_all_files_multiple(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                 monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed')
                        ],
                        files=[
                            TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL),
                            TorrentTrackedFile('file2', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL)
                        ])
    lines = runner.invoke(xirvik, ('rtorrent', 'list-all-files')).output.splitlines()
    assert re.match(r'^/downloads/_completed/file[0-9]$', lines[2])
    assert re.match(r'^/downloads/_completed/file[0-9]$', lines[3])


def _mock_subprocess_shell(mocker: MockerFixture, stdout: str) -> AsyncMock:
    """Mock asyncio.create_subprocess_shell for list_untracked_files tests."""
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (stdout.encode(), b'')
    mock_proc.returncode = 0
    return mocker.patch('asyncio.create_subprocess_shell', return_value=mock_proc)


def test_list_untracked_files_single(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed')
                        ],
                        files=[
                            TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL)
                        ])
    values = '/downloads/_completed/file1\nfile3\n'
    _mock_subprocess_shell(mocker, values)
    lines = runner.invoke(
        xirvik, ('rtorrent', 'list-untracked-files', '-L', 'ssh blah')).output.splitlines()
    assert lines[-1] == 'file3'


def test_list_untracked_files_multiple(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                       monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed')
                        ],
                        files=[
                            TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL),
                            TorrentTrackedFile('file2', 512, 512, 1000, FilePriority.NORMAL,
                                               FileDownloadStrategy.NORMAL)
                        ])
    values = '/downloads/_completed/file1\n/downloads/_completed/file2\nfile3\n'
    _mock_subprocess_shell(mocker, values)
    lines = runner.invoke(
        xirvik, ('rtorrent', 'list-untracked-files', '-L', 'ssh blah')).output.splitlines()
    assert lines[-1] == 'file3'


def test_list_untracked_files_command_fails(runner: CliRunner, mocker: MockerFixture,
                                            tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b'', b'')
    mock_proc.returncode = 1
    mocker.patch('asyncio.create_subprocess_shell', return_value=mock_proc)
    result = runner.invoke(xirvik, ('rtorrent', 'list-untracked-files', '-L', 'false'))
    assert result.exit_code != 0


def test_list_untracked_files_empty_files(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    _patch_client_async(mocker,
                        torrents=[
                            MinimalTorrentDict('hash1',
                                               custom1='TEST me',
                                               name='The Name',
                                               is_hash_checking=False,
                                               base_path='/downloads/_completed')
                        ],
                        files=[])
    values = '/downloads/_completed/file1\n'
    _mock_subprocess_shell(mocker, values)
    lines = runner.invoke(
        xirvik, ('rtorrent', 'list-untracked-files', '-L', 'ssh blah')).output.splitlines()
    assert lines[-1] == '/downloads/_completed/file1'


def test_download_untracked_files(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    mocker.patch('xirvik.commands.simple.setup_logging')
    mock_proc = AsyncMock()
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0
    mocker.patch('asyncio.create_subprocess_exec', return_value=mock_proc)
    mock_conn = mocker.patch('xirvik.commands.simple.Connection')
    mock_conn.return_value.__enter__.return_value = mocker.MagicMock()
    (tmp_path / 'input.txt').write_text('some/dir/file1\nsome/dir/file2\nsome/dir/file2\n')
    assert runner.invoke(xirvik, ('rtorrent', 'download-untracked-files', str(
        tmp_path / 'input.txt'), str(tmp_path / 'output'))).exit_code == 0
    assert mock_proc.wait.call_count == 2


def test_download_untracked_files_rsync_fail(runner: CliRunner, mocker: MockerFixture,
                                             tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    mocker.patch('xirvik.commands.simple.setup_logging')
    mock_proc = AsyncMock()
    mock_proc.wait.return_value = 1
    mock_proc.returncode = 1
    mocker.patch('asyncio.create_subprocess_exec', return_value=mock_proc)
    mock_conn = mocker.patch('xirvik.commands.simple.Connection')
    mock_conn.return_value.__enter__.return_value = mocker.MagicMock()
    (tmp_path / 'input.txt').write_text('some/dir/file1\n')
    result = runner.invoke(xirvik,
                           ('rtorrent', 'download-untracked-files', str(
                               tmp_path / 'input.txt'), str(tmp_path / 'output')))
    assert result.exit_code != 0
