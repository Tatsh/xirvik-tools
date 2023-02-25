"""Command line interface tests."""
# pylint: disable=missing-function-docstring,protected-access
# pylint: disable=redefined-outer-name,missing-class-docstring
from datetime import datetime, timedelta
from os.path import expanduser
from typing import NamedTuple, Optional
import json
import pathlib
import re

from click.testing import CliRunner
from pytest_mock.plugin import MockerFixture
import pytest
import requests_mock as req_mock

from xirvik.typing import (FileDownloadStrategy, FilePriority,
                           TorrentTrackedFile)

from xirvik.commands.root import xirvik


def test_fix_rtorrent(requests_mock: req_mock.Mocker,
                      runner: CliRunner) -> None:
    requests_mock.get('https://some_host.com:443/userpanel/index.php/services/'
                      'restart/rtorrent')
    assert runner.invoke(
        xirvik, ('rtorrent', 'fix', '-H', 'some_host.com')).exit_code == 0


def test_fix_rtorrent_fail(requests_mock: req_mock.Mocker,
                           runner: CliRunner) -> None:
    requests_mock.get(
        'https://some_host.com:443/userpanel/index.php/services/'
        'restart/rtorrent',
        status_code=500)
    assert runner.invoke(
        xirvik, ('rtorrent', 'fix', '-H', 'some_host.com')).exit_code == 1


def test_start_torrents_zero_files(runner: CliRunner, tmp_path: pathlib.Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    assert runner.invoke(xirvik, ('rtorrent', 'add', '-H', 'machine.com',
                                  expanduser('~'))).exit_code == 0


def test_start_torrents_zero_torrent_files(
        runner: CliRunner, tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    non_torrent = tmp_path / 'a.not-a-torrent'
    non_torrent.write_bytes(b'\xFF')
    assert runner.invoke(xirvik, ('rtorrent', 'add', '-H', 'machine.com',
                                  expanduser('~'))).exit_code == 0


def test_start_torrents_normal(runner: CliRunner,
                               requests_mock: req_mock.Mocker,
                               tmp_path: pathlib.Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    torrent = tmp_path / 'a.torrent'
    torrent.write_bytes(b'\xFF')
    m = requests_mock.post(
        'https://machine.com:443/rtorrent/php/addtorrent.php?')
    assert runner.invoke(xirvik, ('rtorrent', 'add', '-H', 'machine.com',
                                  expanduser('~'))).exit_code == 0
    assert not torrent.is_file()
    assert m.called_once is True


def test_start_torrents_error_uploading(
        runner: CliRunner, requests_mock: req_mock.Mocker,
        tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    torrent = tmp_path / 'a.torrent'
    torrent.write_bytes(b'\xFF')
    m = requests_mock.post(
        'https://machine.com:443/rtorrent/php/addtorrent.php?',
        status_code=500)
    assert runner.invoke(xirvik, ('rtorrent', 'add', '-H', 'machine.com',
                                  expanduser('~'))).exit_code == 0
    assert torrent.is_file()
    assert m.called_once is True


def test_start_torrents_start_stopped(runner: CliRunner,
                                      requests_mock: req_mock.Mocker,
                                      tmp_path: pathlib.Path,
                                      monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    torrent = tmp_path / 'a.torrent'
    torrent.write_text('')
    m = requests_mock.post(
        'https://machine.com:443/rtorrent/php/addtorrent.php?')
    assert runner.invoke(xirvik,
                         ('rtorrent', 'add', '--start-stopped', '-d', '-H',
                          'machine.com', expanduser('~'))).exit_code == 0
    assert m.called_once is True
    assert not torrent.is_file()
    assert (m.last_request and m.last_request.text and
            'name="torrents_start_stopped"\r\n\r\non' in m.last_request.text)


def test_add_ftp_user(runner: CliRunner, requests_mock: req_mock.Mocker,
                      tmp_path: pathlib.Path,
                      monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.post(
        'https://machine.com:443/userpanel/index.php/ftp_users/add_user')
    assert runner.invoke(xirvik, ('ftp', 'add-user', '-H', 'machine.com',
                                  'newuser', 'new_pass')).exit_code == 0
    assert m.called_once is True


def test_add_ftp_user_error(runner: CliRunner, requests_mock: req_mock.Mocker,
                            tmp_path: pathlib.Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.post(
        'https://machine.com:443/userpanel/index.php/ftp_users/add_user',
        status_code=500)
    assert runner.invoke(xirvik, ('ftp', 'add-user', '-H', 'machine.com',
                                  'newuser', 'new_pass')).exit_code != 0
    assert m.called_once is True


def test_delete_ftp_user(runner: CliRunner, requests_mock: req_mock.Mocker,
                         tmp_path: pathlib.Path,
                         monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.get(
        ('https://machine.com:443/userpanel/index.php/ftp_users/delete/'
         'bmV3dXNlcg=='))  # cspell: disable-line
    assert runner.invoke(
        xirvik,
        ('ftp', 'delete-user', '-H', 'machine.com', 'newuser')).exit_code == 0
    assert m.called_once is True


def test_delete_ftp_user_error(runner: CliRunner,
                               requests_mock: req_mock.Mocker,
                               tmp_path: pathlib.Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.get(
        ('https://machine.com:443/userpanel/index.php/ftp_users/delete/'
         'bmV3dXNlcg=='),  # cspell: disable-line
        status_code=500)
    assert runner.invoke(
        xirvik,
        ('ftp', 'delete-user', '-H', 'machine.com', 'newuser')).exit_code != 0
    assert m.called_once is True


def test_list_ftp_users(runner: CliRunner, requests_mock: req_mock.Mocker,
                        tmp_path: pathlib.Path,
                        monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    requests_mock.get('https://machine.com:443/userpanel/index.php/ftp_users',
                      text='''<table>
    <tbody>
        <tr class="gradeX">
            <td>some_user</td>
            <td>Yes</td>
            <td>/some_dir</td>
            <td></td>
        </tr>
    </tbody>
</table>''')
    run = runner.invoke(xirvik, ('ftp', 'list-users', '-H', 'machine.com'))
    assert run.exit_code == 0
    assert 'some_user' in run.output
    assert '/some_dir' in run.output


def test_list_ftp_users_error(runner: CliRunner,
                              requests_mock: req_mock.Mocker,
                              tmp_path: pathlib.Path,
                              monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    requests_mock.get('https://machine.com:443/userpanel/index.php/ftp_users',
                      status_code=500)
    assert runner.invoke(
        xirvik, ('ftp', 'list-users', '-H', 'machine.com')).exit_code != 0


def test_authorize_ip(runner: CliRunner, requests_mock: req_mock.Mocker,
                      tmp_path: pathlib.Path,
                      monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.get(
        ('https://machine.com:443/userpanel/index.php/virtual_machine/'
         'authorize_ip'))
    assert runner.invoke(
        xirvik, ('vm', 'authorize-ip', '-H', 'machine.com')).exit_code == 0
    assert m.called_once is True


def test_authorize_ip_error(runner: CliRunner, requests_mock: req_mock.Mocker,
                            tmp_path: pathlib.Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    m = requests_mock.get(
        ('https://machine.com:443/userpanel/index.php/virtual_machine/'
         'authorize_ip'),
        status_code=500)
    assert runner.invoke(
        xirvik, ('vm', 'authorize-ip', '-H', 'machine.com')).exit_code != 0
    assert m.called_once is True


class MinimalTorrentDict(NamedTuple):
    hash: str
    custom1: Optional[str] = None
    left_bytes: int = 0
    name: str = ''
    ratio: float = 0
    creation_date: Optional[datetime] = None
    state_changed: Optional[datetime] = None
    is_hash_checking: bool = False
    base_path: Optional[str] = None
    finished: Optional[datetime] = None


def test_list_torrents(runner: CliRunner, mocker: MockerFixture,
                       tmp_path: pathlib.Path,
                       monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict(
            'hash1',
            custom1='TEST me',
            name='The Name',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed')
    ]
    lines = runner.invoke(xirvik,
                          ('rtorrent', 'list-torrents')).output.splitlines()
    assert re.match(r'^Hash\s+Name\s+Label\s+Finished', lines[0])
    assert re.match(r'^hash1\s+The Name\s+TEST me', lines[1])


def test_list_torrents_json(runner: CliRunner, mocker: MockerFixture,
                            tmp_path: pathlib.Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict(
            'hash1',
            custom1='TEST me',
            name='The Name',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed')
    ]
    data = json.loads(
        runner.invoke(
            xirvik,
            ('rtorrent', 'list-torrents', '-F', 'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['name'] == 'The Name'


def test_list_torrents_json_reversed(runner: CliRunner, mocker: MockerFixture,
                                     tmp_path: pathlib.Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict(
            'hash1',
            custom1='TEST me',
            name='The Name',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed'),
        MinimalTorrentDict(
            'hash2',
            custom1='TEST me',
            name='The Name2',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed')
    ]
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '--reverse-order',
                               '--table-format', 'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash2'
    assert data[1]['hash'] == 'hash1'


def test_list_torrents_json_sort_finished(
        runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict(
            'hash1',
            custom1='TEST me',
            name='The Name',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed',
            finished=datetime.now()),
        MinimalTorrentDict(
            'hash2',
            custom1='TEST me',
            name='The Name2',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed',
            finished=datetime.now() - timedelta(days=7)),
    ]
    data = json.loads(
        runner.invoke(xirvik,
                      ('rtorrent', 'list-torrents', '--sort', 'finished',
                       '--table-format', 'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash2'
    assert data[1]['hash'] == 'hash1'


def test_list_torrents_json_sort_finished_missing(
        runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict(
            'hash1',
            custom1='TEST me',
            name='The Name',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed'),
        MinimalTorrentDict(
            'hash2',
            custom1='TEST me',
            name='The Name2',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed',
            finished=datetime.now() - timedelta(days=7)),
    ]
    data = json.loads(
        runner.invoke(xirvik,
                      ('rtorrent', 'list-torrents', '--sort', 'finished',
                       '--table-format', 'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash1'
    assert data[1]['hash'] == 'hash2'


def test_list_torrents_json_sort_missing_attr(
        runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict(
            'hash1',
            custom1='TEST me',
            name='The Name',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed',
            finished=datetime.now() - timedelta(days=8)),
        MinimalTorrentDict(
            'hash2',
            name='The Name2',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed'),
    ]
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '--sort', 'label',
                               '--table-format', 'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash2'
    assert data[1]['hash'] == 'hash1'


def test_list_torrents_json_sort_other_criteria(
        runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict(
            'hash1',
            custom1='TEST me',
            name='The Name',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed'),
        MinimalTorrentDict(
            'hash2',
            name='AThe Name2',
            is_hash_checking=False,
            base_path=f'/torrents/{client_mock.return_value.name}/_completed'),
    ]
    data = json.loads(
        runner.invoke(xirvik, ('rtorrent', 'list-torrents', '--sort', 'name',
                               '--table-format', 'json')).output.strip())
    assert isinstance(data, list)
    assert data[0]['hash'] == 'hash2'
    assert data[1]['hash'] == 'hash1'


def test_list_files(runner: CliRunner, mocker: MockerFixture,
                    tmp_path: pathlib.Path,
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
        runner.invoke(xirvik, ('rtorrent', 'list-files', '--table-format',
                               'json', 'hash1')).output.strip())
    assert isinstance(data, list)
    assert data[0]['name'] == 'file1'
    assert data[1]['name'] == 'file2'


def test_list_files_reversed(runner: CliRunner, mocker: MockerFixture,
                             tmp_path: pathlib.Path,
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
                      ('rtorrent', 'list-files', '--reverse-order',
                       '--table-format', 'json', 'hash1')).output.strip())
    assert isinstance(data, list)
    assert data[0]['name'] == 'file2'
    assert data[1]['name'] == 'file1'


def test_list_files_sort_size(runner: CliRunner, mocker: MockerFixture,
                              tmp_path: pathlib.Path,
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
        runner.invoke(
            xirvik,
            ('rtorrent', 'list-files', '--table-format', 'json', '--sort',
             'size_bytes', '--reverse-order', 'hash1')).output.strip())
    assert isinstance(data, list)
    assert data[0]['name'] == 'file2'
    assert data[1]['name'] == 'file1'


def test_list_files_normal(runner: CliRunner, mocker: MockerFixture,
                           tmp_path: pathlib.Path,
                           monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.simple.ruTorrentClient')
    client_mock.return_value.list_files.return_value = [
        TorrentTrackedFile('file1', 512, 512, 1000, FilePriority.NORMAL,
                           FileDownloadStrategy.NORMAL),
    ]
    lines = runner.invoke(xirvik,
                          ('rtorrent', 'list-files', '--sort', 'size_bytes',
                           '--reverse-order', 'hash1')).output.splitlines()
    assert re.match(
        r'^Name\s+Size\s+Downloaded Pieces\s+Number of Pieces\s+Priority ID',
        lines[0])
    assert re.match(r'file1\s+1000\s+512\s+512', lines[1])