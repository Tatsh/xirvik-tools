"""move-by-label tests."""
from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from requests.exceptions import HTTPError
from xirvik.commands.root import xirvik

if TYPE_CHECKING:
    from datetime import datetime
    import pathlib

    from click.testing import CliRunner
    from pytest_mock import MockerFixture
    import pytest


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


def test_list_torrents_fail(runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.list_torrents.side_effect = HTTPError
    assert runner.invoke(xirvik, ('rtorrent', 'move-by-label', '-H', 'machine.com')).exit_code != 0
    client_mock.return_value.list_torrents.side_effect = ValueError()
    assert runner.invoke(xirvik, ('rtorrent', 'move-by-label', '-H', 'machine.com')).exit_code != 0


def test_move_torrent(runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
                      monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'some_name'
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='The Label',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    config = tmp_path / 'config'
    config.write_text('{}\n')
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'move-by-label', '-C', str(config), '-H', 'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_called_once_with(
        'hash1', '/downloads/_completed/The Label')


def test_move_torrent_no_label(runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'some_name'
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1=None,
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    assert runner.invoke(xirvik, ('rtorrent', 'move-by-label', '-H', 'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_not_called()


def test_move_torrent_ignored_label(runner: CliRunner, mocker: MockerFixture,
                                    tmp_path: pathlib.Path,
                                    monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'some_name'
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='Ignore-me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    assert runner.invoke(xirvik, ('rtorrent', 'move-by-label', '--ignore-labels', 'Ignore-me', '-H',
                                  'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_not_called()


def test_move_torrent_already_moved(runner: CliRunner, mocker: MockerFixture,
                                    tmp_path: pathlib.Path,
                                    monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'some_name'
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='some_label',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed/some_label')
    ]
    assert runner.invoke(xirvik, ('rtorrent', 'move-by-label', '-H', 'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_not_called()


def test_move_torrent_lower(runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
                            monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    mocker.patch('xirvik.commands.move_by_label.sleep')
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'some_name'
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed')
    ]
    assert runner.invoke(xirvik,
                         ('rtorrent', 'move-by-label', '-l', '-H', 'machine.com')).exit_code == 0
    client_mock.return_value.move_torrent.assert_called_once_with('hash1',
                                                                  '/downloads/_completed/test me')


def test_move_torrent_sleep_after_10(runner: CliRunner, mocker: MockerFixture,
                                     tmp_path: pathlib.Path,
                                     monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_by_label.ruTorrentClient')
    client_mock.return_value.name = 'some_name'
    sleep_mock = mocker.patch('xirvik.commands.move_by_label.sleep')
    tl_len = 10
    torrent_list = [
        MinimalTorrentDict(f'hash{i}',
                           custom1='TEST me',
                           name='The Name',
                           is_hash_checking=False,
                           base_path='/downloads/_completed') for i in range(tl_len)
    ]
    client_mock.return_value.list_torrents.return_value = torrent_list
    assert runner.invoke(
        xirvik, ('rtorrent', 'move-by-label', '-l', '-t', '10', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.move_torrent.call_count == tl_len
    sleep_mock.assert_any_call(tl_len)
