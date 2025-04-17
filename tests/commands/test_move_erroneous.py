"""move-erroneous tests."""
from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

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
    message: str = ''


def test_move_erroneous_normal(runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
                               monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch('xirvik.commands.move_erroneous.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           message='unregistered torrent',
                           custom1='anything',
                           name='Test #1'),
        MinimalTorrentDict('hash2', custom1='anything', name='Test #1'),
    ]
    assert runner.invoke(xirvik, ('rtorrent', 'move-erroneous', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.move_torrent.call_count == 1
    assert client_mock.return_value.remove.call_count == 1
    assert client_mock.return_value.stop.call_count == 2
    assert client_mock.return_value.stop.call_args_list[0].args[0] == 'hash1'
    assert client_mock.return_value.stop.call_args_list[1].args[0] == 'hash1'


def test_move_erroneous_sleep(runner: CliRunner, mocker: MockerFixture, tmp_path: pathlib.Path,
                              monkeypatch: pytest.MonkeyPatch) -> None:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    sleep_mock = mocker.patch('xirvik.commands.move_erroneous.sleep')
    client_mock = mocker.patch('xirvik.commands.move_erroneous.ruTorrentClient')
    ret = [
        MinimalTorrentDict(f'hash{i}',
                           message='unregistered torrent',
                           name=f'Test #{i}',
                           custom1='anything') for i in range(12)
    ]
    client_mock.return_value.list_torrents.return_value = ret
    assert runner.invoke(xirvik, ('rtorrent', 'move-erroneous', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.move_torrent.call_count == 12
    assert client_mock.return_value.remove.call_count == 12
    assert client_mock.return_value.stop.call_count == 24
    assert sleep_mock.call_count == 3
