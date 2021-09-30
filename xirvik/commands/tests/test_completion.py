"""Command line completion tests."""
import pathlib
import pytest

from ..util import complete_hosts, complete_ports

# pylint: disable=missing-function-docstring,protected-access,no-self-use,redefined-outer-name


def test_complete_hosts_blank(tmp_path: pathlib.Path,
                              monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    ssh = tmp_path / '.ssh'
    ssh.mkdir()
    known_hosts = ssh / 'known_hosts'
    known_hosts.write_text('localhost ecda-sha-nistp256 ...\n'
                           'bitbucket.org,131.103.20.167 ssh-rsa ...\n'
                           '[1.1.1.1]:54022  sha-rsa ...\n'
                           '::1 ssh-rsa')
    monkeypatch.setenv('HOME', str(tmp_path))
    hosts = complete_hosts(None, None, '')
    assert 'localhost' in hosts
    assert 'bitbucket.org' in hosts
    assert '131.103.20.167' in hosts
    assert '1.1.1.1' in hosts
    assert 'machine.com' in hosts
    assert '::1' in hosts


def test_complete_hosts_local(tmp_path: pathlib.Path,
                              monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    ssh = tmp_path / '.ssh'
    ssh.mkdir()
    known_hosts = ssh / 'known_hosts'
    known_hosts.write_text('localhost ecda-sha-nistp256 ...\n'
                           'bitbucket.org,131.103.20.167 ssh-rsa ...\n'
                           '[1.1.1.1]:54022  sha-rsa ...\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    hosts = complete_hosts(None, None, 'local')
    assert len(hosts) == 1
    assert 'localhost' in hosts


def test_complete_hosts_no_netrc(tmp_path: pathlib.Path,
                                 monkeypatch: pytest.MonkeyPatch):
    ssh = tmp_path / '.ssh'
    ssh.mkdir()
    known_hosts = ssh / 'known_hosts'
    known_hosts.write_text('localhost ecda-sha-nistp256 ...\n'
                           'bitbucket.org,131.103.20.167 ssh-rsa ...\n'
                           '[1.1.1.1]:54022  sha-rsa ...\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    hosts = complete_hosts(None, None, 'machine')
    assert len(hosts) == 0


def test_complete_hosts_no_known_hosts(tmp_path: pathlib.Path,
                                       monkeypatch: pytest.MonkeyPatch):
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    hosts = complete_hosts(None, None, 'bitbucket.org')
    assert len(hosts) == 0


def test_complete_ports():
    ports = complete_ports(None, None, '8')
    assert len(ports) == 2
    assert '80' in ports


def test_complete_ports_empty():
    ports = complete_ports(None, None, '')
    assert len(ports) == 3
    assert '80' in ports
    assert '8080' in ports
    assert '443' in ports
