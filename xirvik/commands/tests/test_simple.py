"""Command line interface tests."""
from os.path import expanduser
import os
import pathlib

from click.testing import CliRunner
import pytest
import requests_mock as req_mock

from ..root import xirvik

# pylint: disable=missing-function-docstring,protected-access,no-self-use,redefined-outer-name


@pytest.fixture()
def runner():
    return CliRunner()


def test_fix_rtorrent(requests_mock: req_mock.Mocker, runner: CliRunner):
    requests_mock.get('https://somehost.com:443/userpanel/index.php/services/'
                      'restart/rtorrent')
    assert runner.invoke(xirvik,
                         ('rtorrent', 'fix', 'somehost.com')).exit_code == 0


def test_fix_rtorrent_fail(requests_mock: req_mock.Mocker, runner: CliRunner):
    requests_mock.get(
        'https://somehost.com:443/userpanel/index.php/services/'
        'restart/rtorrent',
        status_code=500)
    assert runner.invoke(xirvik,
                         ('rtorrent', 'fix', 'somehost.com')).exit_code == 1


def test_start_torrents_no_auth(runner: CliRunner, tmp_path: pathlib.Path):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    os.environ['HOME'] = str(tmp_path)
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'add', 'machine1.com', expanduser('~'))).exit_code != 0


def test_start_torrents_zero_files(runner: CliRunner, tmp_path: pathlib.Path):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    os.environ['HOME'] = str(tmp_path)
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'add', 'machine.com', expanduser('~'))).exit_code == 0


def test_start_torrents_zero_torrent_files(runner: CliRunner,
                                           tmp_path: pathlib.Path):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    os.environ['HOME'] = str(tmp_path)
    non_torrent = tmp_path / 'a.not-a-torrent'
    non_torrent.write_bytes(b'\xFF')
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'add', 'machine.com', expanduser('~'))).exit_code == 0


def test_start_torrents_normal(runner: CliRunner,
                               requests_mock: req_mock.Mocker,
                               tmp_path: pathlib.Path):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    os.environ['HOME'] = str(tmp_path)
    torrent = tmp_path / 'a.torrent'
    torrent.write_bytes(b'\xFF')
    m = requests_mock.post(
        'https://machine.com:443/rtorrent/php/addtorrent.php?')
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'add', 'machine.com', expanduser('~'))).exit_code == 0
    assert not torrent.is_file()
    assert m.called_once is True


def test_start_torrents_error_uploading(runner: CliRunner,
                                        requests_mock: req_mock.Mocker,
                                        tmp_path: pathlib.Path):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    os.environ['HOME'] = str(tmp_path)
    torrent = tmp_path / 'a.torrent'
    torrent.write_bytes(b'\xFF')
    m = requests_mock.post(
        'https://machine.com:443/rtorrent/php/addtorrent.php?',
        status_code=500)
    assert runner.invoke(
        xirvik,
        ('rtorrent', 'add', 'machine.com', expanduser('~'))).exit_code == 0
    assert torrent.is_file()
    assert m.called_once is True


def test_start_torrents_start_stopped(runner: CliRunner,
                                      requests_mock: req_mock.Mocker,
                                      tmp_path: pathlib.Path):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    os.environ['HOME'] = str(tmp_path)
    torrent = tmp_path / 'a.torrent'
    torrent.write_text('')
    m = requests_mock.post(
        'https://machine.com:443/rtorrent/php/addtorrent.php?')
    assert runner.invoke(
        xirvik, ('rtorrent', 'add', '--start-stopped', '-d', 'machine.com',
                 expanduser('~'))).exit_code == 0
    assert m.called_once is True
    assert not torrent.is_file()
    assert (m.last_request and m.last_request.text and
            'name="torrents_start_stopped"\r\n\r\non' in m.last_request.text)
