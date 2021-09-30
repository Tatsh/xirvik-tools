"""move-erroneous tests."""
import pathlib

from click.testing import CliRunner
from pytest_mock import MockerFixture
import pytest

from ..root import xirvik

# pylint: disable=missing-function-docstring,protected-access,no-self-use,redefined-outer-name


@pytest.fixture()
def runner():
    return CliRunner()


def test_move_erroneous_normal(runner: CliRunner, mocker: MockerFixture,
                               tmp_path: pathlib.Path,
                               monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    client_mock = mocker.patch(
        'xirvik.commands.move_erroneous.ruTorrentClient')
    client_mock.return_value.list_torrents_dict.return_value = {
        'hash1': {
            'message': 'unregistered torrent',
            'is_hash_checking': False,
            'left_bytes': 0,
            'custom1': 'anything',
            'name': 'Test #1',
        },
        'hash2': {
            'message': '',
            'is_hash_checking': False,
            'left_bytes': 0,
            'custom1': 'anything',
            'name': 'Test #1',
        }
    }
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'move-erroneous', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.move_torrent.call_count == 1
    assert client_mock.return_value.remove.call_count == 1
    assert client_mock.return_value.stop.call_count == 2
    assert client_mock.return_value.stop.call_args_list[0].args[0] == 'hash1'
    assert client_mock.return_value.stop.call_args_list[1].args[0] == 'hash1'


def test_move_erroneous_sleep(runner: CliRunner, mocker: MockerFixture,
                              tmp_path: pathlib.Path,
                              monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    sleep_mock = mocker.patch('xirvik.commands.move_erroneous.sleep')
    client_mock = mocker.patch(
        'xirvik.commands.move_erroneous.ruTorrentClient')
    ret = {}
    for i in range(12):
        ret[f'hash{i}'] = {
            'message': 'unregistered torrent',
            'is_hash_checking': False,
            'left_bytes': 0,
            'custom1': 'anything',
            'name': f'Test #{i}',
        }
    client_mock.return_value.list_torrents_dict.return_value = ret
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'move-erroneous', '-H', 'machine.com')).exit_code == 0
    assert client_mock.return_value.move_torrent.call_count == 12
    assert client_mock.return_value.remove.call_count == 12
    assert client_mock.return_value.stop.call_count == 24
    assert sleep_mock.call_count == 3
