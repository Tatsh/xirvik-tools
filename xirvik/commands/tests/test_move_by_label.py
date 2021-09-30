"""move-by-label tests."""
import pathlib

from click.testing import CliRunner
from pytest_mock import MockerFixture
from requests.exceptions import HTTPError
import pytest

from ..root import xirvik

# pylint: disable=missing-function-docstring,protected-access,no-self-use,redefined-outer-name


@pytest.fixture()
def runner():
    return CliRunner()


def _raise_http_error():
    raise HTTPError()


def _raise_value_error():
    raise ValueError()


def test_list_torrents_dict_fail(runner: CliRunner, mocker: MockerFixture,
                                 tmp_path: pathlib.Path,
                                 monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.list_torrents_dict.side_effect = _raise_http_error
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'move-by-label', '-H', 'machine.com')).exit_code != 0
    client_mock.return_value.list_torrents_dict.side_effect = _raise_value_error
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'move-by-label', '-H', 'machine.com')).exit_code != 0


def test_move_torrent(runner: CliRunner, mocker: MockerFixture,
                      tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'somename'
    client_mock.return_value.list_torrents_dict.return_value = {
        'hash1': {
            'custom1': 'The Label',
            'name': 'The Name',
            'is_hash_checking': False,
            'left_bytes': 0,
            'base_path':
            f'/torrents/{client_mock.return_value.name}/_completed'
        }
    }
    assert runner.invoke(xirvik,
                         ('rtorrent', 'move-by-label', '-C', '/dev/null', '-H',
                          'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_called_once_with(
        'hash1',
        f'/torrents/{client_mock.return_value.name}/_completed/The Label')


def test_move_torrent_no_label(runner: CliRunner, mocker: MockerFixture,
                               tmp_path: pathlib.Path,
                               monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'somename'
    client_mock.return_value.list_torrents_dict.return_value = {
        'hash1': {
            'custom1': None,
            'name': 'The Name',
            'is_hash_checking': False,
            'left_bytes': 0,
            'base_path':
            f'/torrents/{client_mock.return_value.name}/_completed'
        }
    }
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'move-by-label', '-H', 'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_not_called()


def test_move_torrent_ignored_label(runner: CliRunner, mocker: MockerFixture,
                                    tmp_path: pathlib.Path,
                                    monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'somename'
    client_mock.return_value.list_torrents_dict.return_value = {
        'hash1': {
            'custom1': 'Ignore-me',
            'name': 'The Name',
            'is_hash_checking': False,
            'left_bytes': 0,
            'base_path':
            f'/torrents/{client_mock.return_value.name}/_completed'
        }
    }
    assert runner.invoke(xirvik,
                         ('rtorrent', 'move-by-label', '--ignore-labels',
                          'Ignore-me', '-H', 'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_not_called()


def test_move_torrent_already_moved(runner: CliRunner, mocker: MockerFixture,
                                    tmp_path: pathlib.Path,
                                    monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'somename'
    client_mock.return_value.list_torrents_dict.return_value = {
        'hash1': {
            'custom1':
            'somelabel',
            'name':
            'The Name',
            'is_hash_checking':
            False,
            'left_bytes':
            0,
            'base_path':
            f'/torrents/{client_mock.return_value.name}/_completed/somelabel'
        }
    }
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'move-by-label', '-H', 'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_not_called()


def test_move_torrent_lower(runner: CliRunner, mocker: MockerFixture,
                            tmp_path: pathlib.Path,
                            monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'somename'
    client_mock.return_value.list_torrents_dict.return_value = {
        'hash1': {
            'custom1': 'TEST me',
            'name': 'The Name',
            'is_hash_checking': False,
            'left_bytes': 0,
            'base_path':
            f'/torrents/{client_mock.return_value.name}/_completed'
        }
    }
    assert runner.invoke(xirvik, ('rtorrent', 'move-by-label', '-l', '-H',
                                  'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_called_once_with(
        'hash1',
        f'/torrents/{client_mock.return_value.name}/_completed/test me')


def test_move_torrent_sleep_after_10(runner: CliRunner, mocker: MockerFixture,
                                     tmp_path: pathlib.Path,
                                     monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'somename'
    sleep_mock = mocker.patch('xirvik.commands.move_by_label.sleep')
    l = []
    for i in range(10):
        l.append((f'hash{i}', {
            'custom1':
            'TEST me',
            'name':
            'The Name',
            'is_hash_checking':
            False,
            'left_bytes':
            0,
            'base_path':
            f'/torrents/{client_mock.return_value.name}/_completed'
        }))
    client_mock.return_value.list_torrents_dict.return_value = dict(l)
    assert runner.invoke(xirvik, ('rtorrent', 'move-by-label', '-l', '-t',
                                  '10', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.move_torrent.call_count == 10
    sleep_mock.assert_called_once_with(10)
