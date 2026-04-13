from __future__ import annotations

from typing import TYPE_CHECKING
import plistlib

from xirvik.commands.install_services import install_services

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner
    from pytest_mock.plugin import MockerFixture


def test_install_services_windows(mocker: MockerFixture, runner: CliRunner) -> None:
    mocker.patch('xirvik.commands.install_services.IS_WINDOWS', True)  # noqa: FBT003
    result = runner.invoke(install_services, ('/', '-H', 'example.com'))
    assert result.exit_code != 0
    assert 'This command is not supported on Windows.' in result.output


def test_install_services_no_xirvik_command(mocker: MockerFixture, runner: CliRunner) -> None:
    mocker.patch('xirvik.commands.install_services.IS_WINDOWS', False)  # noqa: FBT003
    mocker.patch('xirvik.commands.install_services.which', return_value=None)
    result = runner.invoke(install_services, ('/', '-H', 'example.com'))
    assert result.exit_code != 0
    assert 'xirvik command not found.' in result.output


def test_install_services_mac(mocker: MockerFixture, runner: CliRunner) -> None:
    mocker.patch('xirvik.commands.install_services.IS_WINDOWS', False)  # noqa: FBT003
    mocker.patch('xirvik.commands.install_services.IS_MAC', True)  # noqa: FBT003
    mocker.patch('xirvik.commands.install_services.which', return_value='/usr/local/bin/xirvik')
    mocker.patch('xirvik.commands.install_services.Path')
    mock_dump = mocker.patch('xirvik.commands.install_services.plistlib.dump')
    mock_sp_run = mocker.patch('xirvik.commands.install_services.sp.run')
    result = runner.invoke(install_services, ('/', '-H', 'example.com'))
    assert result.exit_code == 0
    assert 'sh.tat.xirvik-start-torrents' in result.output
    mock_dump.assert_called_once_with(
        {
            'Label': 'sh.tat.xirvik-start-torrents',
            'ProgramArguments':
                ['/usr/local/bin/xirvik', 'rtorrent', 'add', '-s', '--host', 'example.com', '/'],
            'StartInterval': 120
        },
        mocker.ANY,
        fmt=plistlib.FMT_XML)
    mock_sp_run.assert_called_once_with(('launchctl', 'load', '-w', mocker.ANY), check=True)


def test_install_services_linux(mocker: MockerFixture, runner: CliRunner, tmp_path: Path) -> None:
    mocker.patch('xirvik.commands.install_services.IS_WINDOWS', False)  # noqa: FBT003
    mocker.patch('xirvik.commands.install_services.IS_MAC', False)  # noqa: FBT003
    mocker.patch('xirvik.commands.install_services.which', return_value='/usr/local/bin/xirvik')
    service_path = tmp_path / 'xirvik-start-torrents.service'
    timer_path = tmp_path / 'xirvik-start-torrents.timer'
    mock_path = mocker.patch('xirvik.commands.install_services.Path')
    mock_path.return_value.expanduser.side_effect = [service_path, timer_path]
    mock_sp_run = mocker.patch('xirvik.commands.install_services.sp.run')
    result = runner.invoke(install_services, ('/', '-H', 'example.com'))
    assert result.exit_code == 0
    service_content = service_path.read_text()
    assert 'ExecStart' in service_content
    assert 'Description' in service_content
    assert 'After' in service_content
    assert 'Type' in service_content
    timer_content = timer_path.read_text()
    assert 'OnCalendar' in timer_content
    assert 'WantedBy' in timer_content
    assert 'Description' in timer_content
    mock_sp_run.assert_any_call(('/bin/systemctl', '--user', 'daemon-reload'), check=True)
    mock_sp_run.assert_any_call(
        ('/bin/systemctl', '--user', 'enable', '--now', 'xirvik-start-torrents.timer'), check=True)
    assert 'Services installed at' in result.output
