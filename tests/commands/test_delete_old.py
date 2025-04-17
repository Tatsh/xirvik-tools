"""delete-old tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, NamedTuple
import xmlrpc.client as xmlrpc

from requests.exceptions import HTTPError
from xirvik.commands.root import xirvik

if TYPE_CHECKING:
    import pathlib

    from click.testing import CliRunner
    from pytest_mock import MockerFixture


class MinimalTorrentDict(NamedTuple):
    hash: str
    custom1: str = ''
    left_bytes: int = 0
    name: str = ''
    ratio: float = 0
    creation_date: datetime | None = None
    state_changed: datetime | None = None


def test_delete_old_list_torrents_fail(runner: CliRunner, mocker: MockerFixture,
                                       tmp_netrc: pathlib.Path) -> None:
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.side_effect = HTTPError
    assert runner.invoke(xirvik, ('rtorrent', 'delete-old', '-H', 'machine.com')).exit_code != 0


def test_delete_old_list_torrents_invalid_for_deletion(runner: CliRunner, mocker: MockerFixture,
                                                       tmp_netrc: pathlib.Path) -> None:
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1', custom1='not the label', left_bytes=100),
        MinimalTorrentDict('hash2', custom1='not the label', left_bytes=0)
    ]
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'delete-old', '--label', 'the-label', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 0


def test_delete_old_list_torrents_dict_invalid_for_deletion2(runner: CliRunner,
                                                             mocker: MockerFixture,
                                                             tmp_netrc: pathlib.Path) -> None:
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1', name='Test #1', custom1='the-label', left_bytes=0)
    ]
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'delete-old', '--label', 'the-label', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 0


def test_delete_old_dry_run(runner: CliRunner, mocker: MockerFixture,
                            tmp_netrc: pathlib.Path) -> None:
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now(timezone.utc) - timedelta(days=14))
    ]
    assert runner.invoke(xirvik, ('rtorrent', 'delete-old', '--dry-run', '--label', 'the-label',
                                  '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 0


def test_delete_old_normal(runner: CliRunner, mocker: MockerFixture,
                           tmp_netrc: pathlib.Path) -> None:
    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now(timezone.utc) - timedelta(days=14))
    ]
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'delete-old', '--label', 'the-label', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 1
    assert sleep_mock.call_count == 1


def test_delete_old_ignore_ratio(runner: CliRunner, mocker: MockerFixture,
                                 tmp_netrc: pathlib.Path) -> None:
    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=0.14,
                           creation_date=datetime.now(timezone.utc) - timedelta(days=14))
    ]
    assert runner.invoke(xirvik, ('rtorrent', 'delete-old', '--label', 'the-label',
                                  '--ignore-ratio', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 1
    assert sleep_mock.call_count == 1


def test_delete_old_ignore_date(runner: CliRunner, mocker: MockerFixture,
                                tmp_netrc: pathlib.Path) -> None:
    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now(timezone.utc) - timedelta(days=14))
    ]
    assert runner.invoke(xirvik, ('rtorrent', 'delete-old', '--label', 'the-label', '--ignore-date',
                                  '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 1
    assert sleep_mock.call_count == 1


def test_delete_old_xmlrpc_fault(runner: CliRunner, mocker: MockerFixture,
                                 tmp_netrc: pathlib.Path) -> None:
    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now(timezone.utc) - timedelta(days=14))
    ]
    client_mock.return_value.delete.side_effect = xmlrpc.Fault(200, 'ss')
    assert runner.invoke(xirvik, ('rtorrent', 'delete-old', '--label', 'the-label',
                                  '--max-attempts', '3', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 3
    assert sleep_mock.call_count == 3


def test_delete_old_protocol_error(runner: CliRunner, mocker: MockerFixture,
                                   tmp_netrc: pathlib.Path) -> None:
    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now(timezone.utc) - timedelta(days=14))
    ]
    client_mock.return_value.delete.side_effect = xmlrpc.ProtocolError(
        'https://machine.com', 500, 'ss', {})
    assert runner.invoke(xirvik, ('rtorrent', 'delete-old', '--label', 'the-label',
                                  '--max-attempts', '3', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 3
    assert sleep_mock.call_count == 3
