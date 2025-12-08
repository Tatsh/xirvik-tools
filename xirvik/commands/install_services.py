"""Install services on Linux and macOS."""
from __future__ import annotations

from configparser import ConfigParser
from os import environ
from pathlib import Path
from shlex import quote
from shutil import which
import platform
import plistlib
import subprocess as sp
import sys

from bascom import setup_logging
import click

from .utils import complete_hosts

IS_MAC = platform.system() == 'Darwin'
IS_WINDOWS = (sys.platform == 'win32' or sys.platform == 'cygwin'
              or environ.get('MSYSTEM', '').lower() == 'msys')


@click.command()
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
@click.option('-i',
              '--interval',
              type=int,
              default=2,
              help='Interval in minutes to check for new torrents.')
@click.option('-H',
              '--host',
              help='Xirvik host (without protocol).',
              shell_complete=complete_hosts,
              required=True)
@click.argument('directories',
                type=click.Path(exists=True, file_okay=False, path_type=Path),
                nargs=-1)
def install_services(directories: tuple[Path, ...],
                     host: str,
                     *,
                     debug: bool = False,
                     interval: int = 2) -> None:
    """Install the xirvik-start-torrents service."""  # noqa: DOC501
    setup_logging(debug=debug, loggers={'xirvik': {}})
    if IS_WINDOWS:
        click.echo('This command is not supported on Windows.')
        raise click.Abort
    xirvik_cmd = which('xirvik')
    if not xirvik_cmd:
        click.echo('xirvik command not found.')
        raise click.Abort
    if IS_MAC:
        label = 'sh.tat.xirvik-start-torrents'
        output_path = Path(f'~/Library/LaunchAgents/{label}.plist').expanduser()
        with output_path.open('w+b') as f:
            plistlib.dump(
                {
                    'Label': label,
                    'ProgramArguments': [
                        xirvik_cmd, 'rtorrent', 'add', '-s', '--host', host, *(str(x)
                                                                               for x in directories)
                    ],
                    'StartInterval': interval * 60,
                },
                f,
                fmt=plistlib.FMT_XML)
        click.echo(f'Service installed at {output_path}.')
        sp.run(('launchctl', 'load', '-w', str(output_path)), check=True)
        click.echo(f'Service loaded. Use `launchctl list {label}` to check its status.')
        return
    # Linux
    service_output_path = Path('~/.config/systemd/user/xirvik-start-torrents.service').expanduser()
    timer_output_path = Path('~/.config/systemd/user/xirvik-start-torrents.timer').expanduser()
    with service_output_path.open('w+') as f:
        parser = ConfigParser(delimiters=('=',))
        parser.optionxform = str  # type: ignore[assignment,method-assign]
        parser['Unit'] = {
            'Description': 'Torrent sync with Xirvik',
            'After': 'network.target',
        }
        dirs_quoted = ' '.join(quote(str(x)) for x in directories)
        parser['Service'] = {
            'Type': 'oneshot',
            'ExecStart': f'{xirvik_cmd} rtorrent add -s --host {host} {dirs_quoted}'
        }
        parser.write(f, space_around_delimiters=False)
    with timer_output_path.open('w+') as f:
        parser = ConfigParser(delimiters=('=',))
        parser.optionxform = str  # type: ignore[assignment,method-assign]
        parser['Unit'] = {'Description': 'Trigger for Xirvik torrent sync'}
        parser['Timer'] = {
            'OnCalendar': f'*-*-* *:0/{interval}:00',
        }
        parser['Install'] = {'WantedBy': 'timers.target'}
        parser.write(f, space_around_delimiters=False)
    click.echo(f'Services installed at {service_output_path} and {timer_output_path}.')
    sp.run(('/bin/systemctl', '--user', 'daemon-reload'), check=True)
    sp.run(('/bin/systemctl', '--user', 'enable', '--now', 'xirvik-start-torrents.timer'),
           check=True)
    click.echo('Timer service enabled and started. Use `systemctl --user status '
               'xirvik-start-torrents.timer` to check its status.')
