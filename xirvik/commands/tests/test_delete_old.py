"""delete-old tests."""
from datetime import datetime, timedelta
from typing import Any, NamedTuple, NoReturn, Optional
import pathlib
import xmlrpc.client as xmlrpc

from click.testing import CliRunner
from pytest_mock import MockerFixture
from requests.exceptions import HTTPError
import pytest

from ..root import xirvik

# pylint: disable=missing-function-docstring,protected-access,no-self-use,redefined-outer-name,unused-argument


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _raise_http_error(*args: Any, **kwargs: Any) -> NoReturn:
    raise HTTPError()


def _raise_fault(*args: Any, **kwargs: Any) -> NoReturn:
    raise xmlrpc.Fault(200, 'ss')


def _raise_protocol_error(*args: Any, **kwargs: Any) -> NoReturn:
    raise xmlrpc.ProtocolError('https://machine.com', 500, 'ss', {})


@pytest.fixture()
def tmp_netrc(tmp_path: pathlib.Path,
              monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    return netrc


class MinimalTorrentDict(NamedTuple):
    hash: str
    custom1: str = ''
    left_bytes: int = 0
    name: str = ''
    ratio: float = 0
    creation_date: Optional[datetime] = None
    state_changed: Optional[datetime] = None


def test_delete_old_list_torrents_fail(
        runner: CliRunner, mocker: MockerFixture, tmp_netrc: pathlib.Path):
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.side_effect = _raise_http_error
    assert runner.invoke(
        xirvik, ('rtorrent', 'delete-old', '-H', 'machine.com')).exit_code != 0


def test_delete_old_list_torrents_invalid_for_deletion(
        runner: CliRunner, mocker: MockerFixture, tmp_netrc: pathlib.Path):
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1', custom1='not the label', left_bytes=100),
        MinimalTorrentDict('hash2', custom1='not the label', left_bytes=0)
    ]
    assert runner.invoke(xirvik,
                         ('rtorrent', 'delete-old', '--label', 'the-label',
                          '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 0


def test_delete_old_list_torrents_dict_invalid_for_deletion2(
        runner: CliRunner, mocker: MockerFixture, tmp_netrc: pathlib.Path):
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           custom1='the-label',
                           left_bytes=0)
    ]
    assert runner.invoke(xirvik,
                         ('rtorrent', 'delete-old', '--label', 'the-label',
                          '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 0


def test_delete_old_dry_run(runner: CliRunner, mocker: MockerFixture,
                            tmp_netrc: pathlib.Path):
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now() - timedelta(days=14))
    ]
    assert runner.invoke(xirvik,
                         ('rtorrent', 'delete-old', '--dry-run', '--label',
                          'the-label', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 0


def test_delete_old_normal(runner: CliRunner, mocker: MockerFixture,
                           tmp_netrc: pathlib.Path):

    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now() - timedelta(days=14))
    ]
    assert runner.invoke(xirvik,
                         ('rtorrent', 'delete-old', '--label', 'the-label',
                          '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 1
    assert sleep_mock.call_count == 1


def test_delete_old_ignore_ratio(runner: CliRunner, mocker: MockerFixture,
                                 tmp_netrc: pathlib.Path):
    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=0.14,
                           creation_date=datetime.now() - timedelta(days=14))
    ]
    assert runner.invoke(
        xirvik, ('rtorrent', 'delete-old', '--label', 'the-label',
                 '--ignore-ratio', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 1
    assert sleep_mock.call_count == 1


def test_delete_old_ignore_date(runner: CliRunner, mocker: MockerFixture,
                                tmp_netrc: pathlib.Path):
    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now() - timedelta(days=14))
    ]
    assert runner.invoke(xirvik,
                         ('rtorrent', 'delete-old', '--label', 'the-label',
                          '--ignore-date', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 1
    assert sleep_mock.call_count == 1


def test_delete_old_xmlrpc_fault(runner: CliRunner, mocker: MockerFixture,
                                 tmp_netrc: pathlib.Path):
    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now() - timedelta(days=14))
    ]
    client_mock.return_value.delete.side_effect = _raise_fault
    assert runner.invoke(
        xirvik, ('rtorrent', 'delete-old', '--label', 'the-label',
                 '--max-attempts', '3', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 3
    assert sleep_mock.call_count == 3


def test_delete_old_protocol_error(runner: CliRunner, mocker: MockerFixture,
                                   tmp_netrc: pathlib.Path):
    sleep_mock = mocker.patch('xirvik.commands.delete_old.sleep')
    client_mock = mocker.patch('xirvik.commands.delete_old.ruTorrentClient')
    client_mock.return_value.list_torrents.return_value = [
        MinimalTorrentDict('hash1',
                           name='Test #1',
                           left_bytes=0,
                           custom1='the-label',
                           ratio=2,
                           creation_date=datetime.now() - timedelta(days=14))
    ]
    client_mock.return_value.delete.side_effect = _raise_protocol_error
    assert runner.invoke(
        xirvik, ('rtorrent', 'delete-old', '--label', 'the-label',
                 '--max-attempts', '3', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.delete.call_count == 3
    assert sleep_mock.call_count == 3
