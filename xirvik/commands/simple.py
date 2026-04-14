"""Mirror (copy data from remote to local) helper."""
from __future__ import annotations

from base64 import b64encode
from datetime import MINYEAR, datetime, timezone
from logging.handlers import SysLogHandler
from os.path import realpath
from pathlib import Path
from shlex import quote
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any, NoReturn, cast
import asyncio
import functools
import json
import logging
import re
import signal
import sys

from bascom import setup_logging
from bs4 import BeautifulSoup as Soup
from fabric import Connection  # type: ignore[import-untyped]
from niquests.exceptions import HTTPError
from tabulate import tabulate, tabulate_formats
from unidecode import unidecode
from xirvik.client import ruTorrentClient
import anyio
import click
import niquests

from .utils import command_with_config_file, complete_hosts, complete_ports

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from logging.config import _HandlerConfiguration

    from xirvik.typing import TorrentInfo

log = logging.getLogger(__name__)


def _ctrl_c_handler(_: int, __: Any) -> NoReturn:  # pragma: no cover
    msg = 'Signal raised.'
    raise SystemExit(msg)


@click.command(cls=command_with_config_file('config', 'add-torrents'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.argument('directories',
                type=click.Path(exists=True, file_okay=False, path_type=Path),
                nargs=-1)
@click.option('--no-verify',
              default=False,
              is_flag=True,
              help='Disable TLS verification (not recommended).')
@click.option('--start-stopped', is_flag=True, help='Start torrents in stopped state.')
@click.option('-C', '--config', help='Configuration file.')
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-s', '--syslog', is_flag=True, help='Enable syslog logging.')
def start_torrents(
        host: str,
        directories: tuple[Path, ...],
        port: int = 443,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False,
        start_stopped: bool = False,
        syslog: bool = False,
        no_verify: bool = False) -> None:
    """Upload torrent files to the server."""
    async def _main() -> None:
        signal.signal(signal.SIGINT, _ctrl_c_handler)
        handlers: dict[str, _HandlerConfiguration] = {}
        handlers_tuple: tuple[str, ...] = ()
        if syslog:  # pragma: no cover
            handlers = {
                'syslog': {
                    'address': '/dev/log' if Path('/dev/log').exists() else '/var/run/syslog',
                    'formatter': logging.Formatter('xirvik: %(message)s'),
                    'class': SysLogHandler,
                }
            }
            handlers_tuple = ('syslog',)
        setup_logging(debug=debug,
                      handlers=handlers,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {
                              'handlers': handlers_tuple,
                              'propagate': False,
                          } if handlers_tuple else {}
                      })
        cache_dir = Path(realpath(Path('~/.cache/xirvik').expanduser()))
        cache_dir.mkdir(parents=True, exist_ok=True)
        post_url = f'https://{host:s}:{port:d}/rtorrent/php/addtorrent.php?'
        form_data: dict[str, str] = {}
        if start_stopped:
            form_data['torrents_start_stopped'] = 'on'
        for d in (Path(x) for x in directories):
            for item in d.iterdir():
                if not item.name.lower().endswith('.torrent'):
                    continue
                prefix = f'{item.name:s}-'
                with NamedTemporaryFile(prefix=prefix,
                                        suffix='.torrent',
                                        dir=cache_dir,
                                        delete=False) as w:
                    w.write(item.read_bytes())
                    old = item
                torrent_content = await anyio.Path(w.name).read_bytes()
                filename = unidecode(w.name)
                log.info('Uploading torrent %s (actual name: "%s").',
                         Path(item).name,
                         Path(filename).name)
                resp = await niquests.apost(post_url,
                                            data=form_data,
                                            files={'torrent_file': (filename, torrent_content)},
                                            verify=not no_verify,
                                            timeout=30)
                if not resp.ok:
                    log.error('Error uploading %s.', old)
                    continue
                log.debug('Deleting %s.', old)
                await anyio.Path(old).unlink()

    asyncio.run(_main())


@click.command(cls=command_with_config_file('config', 'list-ftp-users'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file.')
def list_ftp_users(
        host: str,
        port: int = 443,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """List FTP users."""
    async def _main() -> None:
        setup_logging(debug=debug,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        r = await niquests.aget(f'https://{host}:{port:d}/userpanel/index.php/ftp_users',
                                timeout=30)
        try:
            r.raise_for_status()
        except HTTPError as e:
            raise click.Abort from e
        content = Soup(r.text or '', 'html5lib').select('.gradeX td')
        click.echo(
            tabulate(((user.text, read_only.text == 'Yes', root_dir.text)
                      for user, read_only, root_dir, _ in (content[i:i + 4]
                                                           for i in range(0, len(content), 4))),
                     headers=('Username', 'Read-only', 'Root directory')))

    asyncio.run(_main())


@click.command(cls=command_with_config_file('config', 'add-ftp-user'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
@click.option('-r', '--root-directory', default='/', help='Root directory for the FTP user.')
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file.')
@click.argument('username')
@click.argument('password')
def add_ftp_user(
        host: str,
        username: str,
        password: str,
        port: int = 443,
        root_directory: str = '/',
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """Add an FTP user."""
    async def _main() -> None:
        setup_logging(debug=debug,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        uri = (f'https://{host}:{port:d}/userpanel/index.php/'
               'ftp_users/add_user')
        root_dir = root_directory if root_directory.startswith('/') else f'/{root_directory}'
        r = await niquests.apost(uri,
                                 data={
                                     'username': username,
                                     'password_1': password,
                                     'root_folder': root_dir,
                                     'read_only': 'no'
                                 },
                                 timeout=30)
        try:
            r.raise_for_status()
        except HTTPError as e:
            raise click.Abort from e

    asyncio.run(_main())


@click.command(cls=command_with_config_file('config', 'delete-ftp-user'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file.')
@click.argument('username')
def delete_ftp_user(
        host: str,
        username: str,
        port: int = 443,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """Delete an FTP user."""
    async def _main() -> None:
        setup_logging(debug=debug,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        user = b64encode(username.encode()).decode()
        uri = (f'https://{host}:{port:d}/userpanel/index.php/ftp_users/'
               f'delete/{user}')
        r = await niquests.aget(uri, timeout=30)
        try:
            r.raise_for_status()
        except HTTPError as e:
            raise click.Abort from e

    asyncio.run(_main())


@click.command(cls=command_with_config_file('config', 'authorize-ip'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file.')
def authorize_ip(
        host: str,
        port: int = 443,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """Authorise the current IP for access to the VM via SSH/VNC/RDP."""
    async def _main() -> None:
        setup_logging(debug=debug,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        uri = (f'https://{host}:{port:d}/userpanel/index.php/virtual_machine/'
               'authorize_ip')
        r = await niquests.aget(uri, timeout=30)
        try:
            r.raise_for_status()
        except HTTPError as e:
            raise click.Abort from e

    asyncio.run(_main())


@click.command(cls=command_with_config_file('config', 'fix-rtorrent'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file.')
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
def fix_rtorrent(
        host: str,
        port: int,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """Restart the rtorrent service in case ruTorrent cannot connect to it."""
    async def _main() -> None:
        setup_logging(debug=debug,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        log.info('No guarantees this will work!')
        uri = (f'https://{host}:{port:d}/userpanel/index.php/services/'
               'restart/rtorrent')
        r = await niquests.aget(uri, timeout=30)
        try:
            r.raise_for_status()
        except HTTPError as e:
            raise click.Abort from e

    asyncio.run(_main())


STATES_FOR_SORTING = {'finished', 'creation_date', 'state_changed'}


@click.command(cls=command_with_config_file('config', 'list-torrents'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file.')
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
@click.option('-I', '--no-headers', is_flag=True, help='Omit table headers.')
@click.option('-F',
              '--table-format',
              type=click.Choice([*tabulate_formats, 'json']),
              default='plain',
              help='Output table format.')
@click.option('-S',
              '--sort',
              type=click.Choice(
                  ('name', 'hash', 'label', 'creation_date', 'state_changed', 'finished')),
              help='Field to sort by.')
@click.option('-R', '--reverse-order', is_flag=True, help='Reverse the sort order.')
def list_torrents(
        host: str,
        config: str | None = None,  # noqa: ARG001
        table_format: str = 'plain',
        sort: str | None = None,
        *,
        debug: bool = False,
        no_headers: bool = False,
        port: int = 443,
        reverse_order: bool | None = None) -> None:
    """List torrents in a given format."""
    async def _main() -> None:
        setup_logging(debug=debug,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        min_tz_aware = datetime(MINYEAR, 1, 1, tzinfo=timezone.utc)

        def sorter(x: TorrentInfo) -> Any:
            sort_key = sort or ''
            if ((val := getattr(x, sort_key if sort_key != 'label' else 'custom1', None)) is None
                    and sort in STATES_FOR_SORTING):
                return min_tz_aware
            return val or ''

        torrents = cast('list[TorrentInfo] | Sequence[TorrentInfo]',
                        [info async for info in ruTorrentClient(f'{host}:{port}').list_torrents()])
        if sort:
            torrents = sorted(torrents, key=sorter)
        if reverse_order:
            torrents = list(reversed(list(torrents)))
        match table_format:
            case fmt if fmt in tabulate_formats:
                click.echo_via_pager(
                    tabulate(((t.hash, t.name, t.custom1, t.finished) for t in torrents),
                             headers=() if no_headers else ('Hash', 'Name', 'Label', 'Finished'),
                             tablefmt=table_format))
            case 'json':
                click.echo(
                    json.dumps([{
                        'hash': x.hash,
                        'name': x.name,
                        'label': x.custom1,
                        'finished': x.finished.isoformat() if x.finished else None,
                        'base_path': x.base_path
                    } for x in torrents]))
            case _:  # pragma no cover
                click.echo('Invalid table format specified.', err=True)
                raise click.Abort

    asyncio.run(_main())


@click.command(cls=command_with_config_file('config', 'list-files'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file.')
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
@click.option('-I', '--no-headers', is_flag=True, help='Omit table headers.')
@click.option('-F',
              '--table-format',
              type=click.Choice([*tabulate_formats, 'json']),
              default='plain',
              help='Output table format.')
@click.option('-S',
              '--sort',
              type=click.Choice(('name', 'size_bytes', 'priority')),
              default='name',
              help='Field to sort by.')
@click.option('-R', '--reverse-order', is_flag=True, help='Reverse the sort order.')
@click.argument('hash')
def list_files(
        hash: str,  # noqa: A002
        host: str,
        port: int,
        config: str | None = None,  # noqa: ARG001
        table_format: str = 'plain',
        sort: str = 'name',
        *,
        debug: bool = False,
        no_headers: bool = False,
        reverse_order: bool | None = None) -> None:
    """List a torrent's files in a given format."""
    async def _main() -> None:
        setup_logging(debug=debug,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        files = sorted([f async for f in ruTorrentClient(f'{host}:{port}').list_files(hash)],
                       key=lambda x: getattr(x, sort))
        if reverse_order:
            files = list(reversed(files))
        match table_format:
            case fmt if fmt in tabulate_formats:
                click.echo_via_pager(
                    tabulate(
                        ((f.name, f.size_bytes, f.downloaded_pieces, f.number_of_pieces,
                          str(f.priority_id)) for f in files),
                        headers=() if no_headers else
                        ('Name', 'Size', 'Downloaded Pieces', 'Number of Pieces', 'Priority ID'),
                        tablefmt=table_format))
            case 'json':
                click.echo(json.dumps([x._asdict() for x in files]))
            case _:  # pragma no cover
                click.echo('Invalid table format specified.', err=True)
                raise click.Abort

    asyncio.run(_main())


def _resolve_single_file_torrent_path(info: TorrentInfo, filename: str) -> str:
    if not info.base_path.endswith(filename):
        return f'{info.base_path}/{filename}'
    return info.base_path


@click.command(cls=command_with_config_file('config', 'list-all-files'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file.')
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
def list_all_files(
        host: str,
        port: int,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """List every tracked file."""
    async def _main() -> None:
        setup_logging(debug=debug,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        client = ruTorrentClient(f'{host}:{port}')
        click.echo('Listing torrents ...', file=sys.stderr)
        all_torrents = [info async for info in client.list_torrents()]
        with click.progressbar(all_torrents, file=sys.stderr,
                               label='Getting file list') as progress_bar:
            info: TorrentInfo
            for info in progress_bar:
                files = [f async for f in client.list_files(info.hash)]
                if len(files) == 1:
                    click.echo(_resolve_single_file_torrent_path(info, files[0].name))
                else:
                    for file in (f'{info.base_path}/{y.name}' for y in files):
                        click.echo(file)

    asyncio.run(_main())


@click.command(cls=command_with_config_file('config', 'list-untracked-files'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-L',
              '--server-list-command',
              help=('This should be a command that outputs lines where each line is a '
                    'complete file path that matches the "torrents/<username>/..." output '
                    "from ruTorrent's API. An example using SSH:\n\n    "
                    "ssh name-of-server 'find /media/sf_hostshare -type f' | "
                    "sed -re 's|^/media/sf_hostshare|/torrents/username|g'."))
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
def list_untracked_files(
        host: str,
        port: int,
        server_list_command: str,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """List all files on the server that are not tracked."""
    async def _main() -> None:
        def fix_path(res: str) -> str:
            return re.sub(fr'^/torrents/{client.name}/', '/downloads/', res)

        setup_logging(debug=debug,
                      loggers={
                          'urllib3': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        click.echo('Getting server-side file list', file=sys.stderr)
        proc = await asyncio.create_subprocess_shell(server_list_command,
                                                     stdout=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            msg = f'Server list command failed with exit code {proc.returncode}'
            raise click.ClickException(msg)
        server_files = stdout.decode().splitlines()
        client = ruTorrentClient(f'{host}:{port}')
        click.echo('Listing torrents ...', file=sys.stderr)
        all_torrents = [info async for info in client.list_torrents()]
        with click.progressbar(all_torrents, file=sys.stderr,
                               label='Getting file list') as progress_bar:
            info: TorrentInfo
            for info in progress_bar:
                log.debug('Torrent: %s', info.name)
                files = [f async for f in client.list_files(info.hash)]
                if not files:
                    continue
                if len(files) == 1:
                    res = fix_path(_resolve_single_file_torrent_path(info, files[0].name))
                    log.debug('Single file: %s', res)
                    try:
                        server_files.remove(res)
                    except ValueError:  # pragma: no cover
                        log.debug('Unknown file (%s): %s', info.name, res)
                else:
                    for file in (fix_path(f'{info.base_path}/{y.name}') for y in files):
                        log.debug('File: %s', file)
                        try:
                            server_files.remove(file)
                        except ValueError:  # pragma: no cover
                            log.debug('Unknown file (%s): %s', info.name, file)
        for file in sorted(server_files):
            click.echo(file)

    asyncio.run(_main())


@click.command(cls=command_with_config_file('config', 'download-untracked-files'),
               context_settings={'help_option_names': ('-h', '--help')})
@click.argument('untracked-filename', type=click.Path(exists=True, path_type=Path))
@click.argument('target', type=click.Path(path_type=Path))
@click.option('-H', '--host', help='Xirvik host (without protocol).', shell_complete=complete_hosts)
@click.option('-p',
              '--port',
              type=int,
              default=443,
              help='Server port.',
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True, help='Enable debug level logging.')
@click.option('-u', '--username', help='SSH user name.')
def download_untracked_files(
        host: str,
        port: int,
        target: Path,
        untracked_filename: Path,
        config: str | None = None,  # noqa: ARG001
        username: str | None = None,
        *,
        debug: bool = False) -> None:
    """Download untracked files using rsync."""
    async def _main() -> None:
        setup_logging(debug=debug,
                      loggers={
                          'fabric': {},
                          'paramiko': {},
                          'urllib3.util.retry': {
                              'level': 'WARNING'
                          },
                          'xirvik': {}
                      })
        processed: set[str] = set()

        def get_lines() -> Iterator[str]:
            with untracked_filename.open(encoding='utf-8') as f:
                for file_or_dir in (f'/downloads/{"/".join(x.strip().split("/")[2:5])}' for x in f):
                    if file_or_dir not in processed:
                        processed.add(file_or_dir)
                        yield file_or_dir

        def _is_dir_sync(conn: Connection, path: str) -> bool:
            return bool(
                conn.run(f'stat -c %F {quote(path)}', hide=True).stdout.strip() == 'directory')

        with Connection(host, port=port, user=username) as conn:
            for file_or_dir in get_lines():
                out_file_or_dir = target / '/'.join(file_or_dir.split('/')[2:])
                await anyio.Path(out_file_or_dir.parent).mkdir(parents=True, exist_ok=True)
                is_directory = await anyio.to_thread.run_sync(
                    functools.partial(_is_dir_sync, conn, file_or_dir))
                src = f'{host}:{file_or_dir}{"/" if is_directory else ""}'
                proc = await asyncio.create_subprocess_exec('rsync', '-e', f'ssh -p {port}',
                                                            '--progress', '-lrtNEU',
                                                            *(('-v',) if debug else ()), src,
                                                            str(out_file_or_dir))
                if (await proc.wait()) != 0:
                    msg = f'rsync failed with exit code {proc.returncode}'
                    raise click.ClickException(msg)
                log.info('Finished downloading `%s` to `%s`.', src, out_file_or_dir)

    asyncio.run(_main())
