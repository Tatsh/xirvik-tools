"""Command line interface tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
import json
import re

from xirvik.commands.root import xirvik
from xirvik.typing import FileDownloadStrategy, FilePriority, TorrentTrackedFile

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock.plugin import MockerFixture
    import pytest
    import requests_mock as req_mock


def test_fix_rtorrent(requests_mock: req_mock.Mocker, runner: CliRunner) -> None:
    requests_mock.get('https://some_host.com:443/userpanel/index.php/services/'
                      'restart/rtorrent')
    assert runner.invoke(xirvik, ('rtorrent', 'fix', '-H', 'some_host.com')).exit_code == 0


def test_fix_rtorrent_fail(requests_mock: req_mock.Mocker, runner: CliRunner) -> None:
    requests_mock.get('https://some_host.com:443/userpanel/index.php/services/'
                      'restart/rtorrent',
                      status_code=500)
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


def test_start_torrents_normal(runner: CliRunner, requests_mock: req_mock.Mocker, tmp_path: Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    torrent = tmp_path / 'a.torrent'
    torrent.write_bytes(b'\xFF')
    m = requests_mock.post('https://machine.com:443/rtorrent/php/addtorrent.php?')
    assert runner.invoke(xirvik,
                         ('rtorrent', 'add', '-H', 'machine.com', str(Path.home()))).exit_code == 0
    assert not torrent.is_file()
    assert m.called_once is True


def test_start_torrents_error_uploading(runner: CliRunner, requests_mock: req_mock.Mocker,
                                        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    torrent = tmp_path / 'a.torrent'
    torrent.write_bytes(b'\xFF')
    m = requests_mock.post('https://machine.com:443/rtorrent/php/addtorrent.php?', status_code=500)
    assert runner.invoke(xirvik,
                         ('rtorrent', 'add', '-H', 'machine.com', str(Path.home()))).exit_code == 0
    assert torrent.is_file()
    assert m.called_once is True


def test_start_torrents_start_stopped(runner: CliRunner, requests_mock: req_mock.Mocker,
                                      tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    torrent = tmp_path / 'a.torrent'
    torrent.write_text('')
    m = requests_mock.post('https://machine.com:443/rtorrent/php/addtorrent.php?')
    assert runner.invoke(xirvik, ('rtorrent', 'add', '--start-stopped', '-d', '-H', 'machine.com',
                                  str(Path.home()))).exit_code == 0
    assert m.called_once is True
    assert not torrent.is_file()
    assert m.last_request
    assert m.last_request.text
    assert 'name="torrents_start_stopped"\r\n\r\non' in m.last_request.text


def test_add_ftp_user(runner: CliRunner, requests_mock: req_mock.Mocker, tmp_path: Path,
                      monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.post('https://machine.com:443/userpanel/index.php/ftp_users/add_user')
    assert runner.invoke(
        xirvik, ('ftp', 'add-user', '-H', 'machine.com', 'newuser', 'new_pass')).exit_code == 0
    assert m.called_once is True


def test_add_ftp_user_error(runner: CliRunner, requests_mock: req_mock.Mocker, tmp_path: Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.post('https://machine.com:443/userpanel/index.php/ftp_users/add_user',
                           status_code=500)
    assert runner.invoke(
        xirvik, ('ftp', 'add-user', '-H', 'machine.com', 'newuser', 'new_pass')).exit_code != 0
    assert m.called_once is True


def test_delete_ftp_user(runner: CliRunner, requests_mock: req_mock.Mocker, tmp_path: Path,
                         monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.get('https://machine.com:443/userpanel/index.php/ftp_users/delete/'
                          'bmV3dXNlcg==')  # cspell: disable-line
    assert runner.invoke(xirvik,
                         ('ftp', 'delete-user', '-H', 'machine.com', 'newuser')).exit_code == 0
    assert m.called_once is True


def test_delete_ftp_user_error(runner: CliRunner, requests_mock: req_mock.Mocker, tmp_path: Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.get(
        ('https://machine.com:443/userpanel/index.php/ftp_users/delete/'
         'bmV3dXNlcg=='),  # cspell: disable-line
        status_code=500)
    assert runner.invoke(xirvik,
                         ('ftp', 'delete-user', '-H', 'machine.com', 'newuser')).exit_code != 0
    assert m.called_once is True


def test_list_ftp_users(runner: CliRunner, requests_mock: req_mock.Mocker, tmp_path: Path,
                        monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    requests_mock.get('https://machine.com:443/userpanel/index.php/ftp_users',
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


def test_list_ftp_users_error(runner: CliRunner, requests_mock: req_mock.Mocker, tmp_path: Path,
                              monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    requests_mock.get('https://machine.com:443/userpanel/index.php/ftp_users', status_code=500)
    assert runner.invoke(xirvik, ('ftp', 'list-users', '-H', 'machine.com')).exit_code != 0


def test_authorize_ip(runner: CliRunner, requests_mock: req_mock.Mocker, tmp_path: Path,
                      monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.get('https://machine.com:443/userpanel/index.php/virtual_machine/'
                          'authorize_ip')
    assert runner.invoke(xirvik, ('vm', 'authorize-ip', '-H', 'machine.com')).exit_code == 0
    assert m.called_once is True


def test_authorize_ip_error(runner: CliRunner, requests_mock: req_mock.Mocker, tmp_path: Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.get(('https://machine.com:443/userpanel/index.php/virtual_machine/'
                           'authorize_ip'),
                          status_code=500)
    assert runner.invoke(xirvik, ('vm', 'authorize-ip', '-H', 'machine.com')).exit_code != 0
    assert m.called_once is True


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


def test_list_torrents(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                       monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    lines = runner.invoke(xirvik, ('rtorrent', 'list-torrents')).output.splitlines()
    assert re.match(r'^Hash\s+Name\s+Label\s+Finished', lines[0])
    assert re.match(r'^hash1\s+The Name\s+TEST me', lines[1])


def test_list_torrents_json(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '-F', 'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['name'] == 'The Name'


def test_list_torrents_json_reversed(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
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
    ]
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
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed',
                           finished=datetime.now(timezone.utc)),
        MinimalTorrentDict('hash2',
                           custom1='TEST me',
                           name='The Name2',
                           is_hash_checking=False,
                           base_path='/downloads/_completed',
                           finished=datetime.now(timezone.utc) - timedelta(days=7)),
    ]
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
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed'),
        MinimalTorrentDict('hash2',
                           custom1='TEST me',
                           name='The Name2',
                           is_hash_checking=False,
                           base_path='/downloads/_completed',
                           finished=datetime.now(timezone.utc) - timedelta(days=7)),
    ]
    runner.invoke(xirvik, ('rtorrent', 'list-torrents', '--sort', 'finished', '--table-format',
                           'json')).output.strip()
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
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed',
                           finished=datetime.now(timezone.utc) - timedelta(days=8)),
        MinimalTorrentDict('hash2',
                           name='The Name2',
                           is_hash_checking=False,
                           base_path='/downloads/_completed'),
    ]
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
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed'),
        MinimalTorrentDict('hash2',
                           name='AThe Name2',
                           is_hash_checking=False,
                           base_path='/downloads/_completed'),
    ]
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
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
        TorrentTrackedFile('file2', 512, 512, 1200, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
    ]
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
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
        TorrentTrackedFile('file2', 512, 512, 1200, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
    ]
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
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
        TorrentTrackedFile('file2', 512, 512, 1200, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
    ]
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
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
    ]
    lines = runner.invoke(xirvik, ('rtorrent', 'list-files', '--sort', 'size_bytes',
                                   '--reverse-order', 'hash1')).output.splitlines()
    assert re.match(r'^Name\s+Size\s+Downloaded Pieces\s+Number of Pieces\s+Priority ID', lines[0])
    assert re.match(r'file1\s+1000\s+512\s+512', lines[1])


def test_list_all_files_single(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL)
    ]
    lines = runner.invoke(xirvik, ('rtorrent', 'list-all-files')).output.splitlines()
    assert re.match(r'^/downloads/_completed/file[0-9]$', lines[2])


def test_list_all_files_single_alt(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """Handle when the torrent contains a single file inside a directory of the same name."""
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed/file1')
    ]
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL)
    ]
    lines = runner.invoke(xirvik, ('rtorrent', 'list-all-files')).output.splitlines()
    assert re.match(r'^/downloads/_completed/file[0-9]$', lines[2])


def test_list_all_files_multiple(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                 monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
        TorrentTrackedFile('file2', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL)
    ]
    lines = runner.invoke(xirvik, ('rtorrent', 'list-all-files')).output.splitlines()
    assert re.match(r'^/downloads/_completed/file[0-9]$', lines[2])
    assert re.match(r'^/downloads/_completed/file[0-9]$', lines[3])


def test_list_untracked_files_single(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL)
    ]
    sp_mock = mocker.patch('xirvik.commands.simple.sp')
    values = ['/downloads/_completed/file1', 'file3', '']

    sp_mock.run.return_value.stdout = '\n'.join(values)
    lines = runner.invoke(
        xirvik, ('rtorrent', 'list-untracked-files', '-L', 'ssh blah')).output.splitlines()
    assert lines[-1] == 'file3'


def test_list_untracked_files_multiple(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                       monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
        TorrentTrackedFile('file2', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL)
    ]
    sp_mock = mocker.patch('xirvik.commands.simple.sp')
    values = ['/downloads/_completed/file1', '/downloads/_completed/file2', 'file3', '']

    sp_mock.run.return_value.stdout = '\n'.join(values)
    lines = runner.invoke(
        xirvik, ('rtorrent', 'list-untracked-files', '-L', 'ssh blah')).output.splitlines()
    assert lines[-1] == 'file3'


def test_download_untracked_files(runner: CliRunner, mocker: MockerFixture, tmp_path: Path,
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    mocker.patch('xirvik.commands.simple.setup_logging')
    mock_run = mocker.patch('xirvik.commands.simple.sp.run')
    mock_conn = mocker.patch('xirvik.commands.simple.Connection')
    mock_conn.return_value.__enter__.return_value = mocker.MagicMock()
    (tmp_path / 'input.txt').write_text('some/dir/file1\nsome/dir/file2\nsome/dir/file2\n')
    assert runner.invoke(xirvik, ('rtorrent', 'download-untracked-files', str(
        tmp_path / 'input.txt'), str(tmp_path / 'output'))).exit_code == 0
    assert mock_run.call_count == 2
