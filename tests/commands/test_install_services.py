from __future__ import annotations

from typing import TYPE_CHECKING
import plistlib

from xirvik.commands.install_services import install_services

if TYPE_CHECKING:
    from click.testing import CliRunner
    from pytest_mock.plugin import MockerFixture


def test_install_services_windows(mocker: MockerFixture, runner: CliRunner) -> None:
    """Test that the install_services command does not run on Windows."""
    mocker.patch('xirvik.commands.install_services.IS_WINDOWS', True)  # noqa: FBT003
    result = runner.invoke(install_services, ('/', '-H', 'example.com'))
    assert result.exit_code != 0
    assert 'This command is not supported on Windows.' in result.output


def test_install_services_no_xirvik_command(mocker: MockerFixture, runner: CliRunner) -> None:
    """Test that the install_services command fails if xirvik command is not found."""
    mocker.patch('xirvik.commands.install_services.IS_WINDOWS', False)  # noqa: FBT003
    mocker.patch('xirvik.commands.install_services.which', return_value=None)
    result = runner.invoke(install_services, ('/', '-H', 'example.com'))
    assert result.exit_code != 0
    assert 'xirvik command not found.' in result.output


def test_install_services_mac(mocker: MockerFixture, runner: CliRunner) -> None:
    """Test that the install_services command runs on macOS."""
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


def test_install_services_linux(mocker: MockerFixture, runner: CliRunner) -> None:
    """Test that the install_services command runs on Linux."""
    mocker.patch('xirvik.commands.install_services.IS_WINDOWS', False)  # noqa: FBT003
    mocker.patch('xirvik.commands.install_services.IS_MAC', False)  # noqa: FBT003
    mocker.patch('xirvik.commands.install_services.which', return_value='/usr/local/bin/xirvik')
    mocker.patch('xirvik.commands.install_services.Path')
    mock_parser = mocker.patch('xirvik.commands.install_services.ConfigParser')
    mock_sp_run = mocker.patch('xirvik.commands.install_services.sp.run')
    result = runner.invoke(install_services, ('/', '-H', 'example.com'))
    assert result.exit_code == 0
    mock_parser.return_value.write.assert_called_with(mocker.ANY, space_around_delimiters=False)
    mock_sp_run.assert_any_call(('/bin/systemctl', '--user', 'daemon-reload'), check=True)
    mock_sp_run.assert_any_call(
        ('/bin/systemctl', '--user', 'enable', '--now', 'xirvik-start-torrents.timer'), check=True)
    assert 'Services installed at' in result.output
