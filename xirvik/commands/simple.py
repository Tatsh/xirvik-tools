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
import json
import logging
import re
import signal
import subprocess as sp
import sys

from bascom import setup_logging
from bs4 import BeautifulSoup as Soup
from fabric import Connection  # type: ignore[import-untyped]
from requests.exceptions import HTTPError
from tabulate import tabulate, tabulate_formats
from unidecode import unidecode
from xirvik.client import ruTorrentClient
import click
import requests

from .utils import command_with_config_file, complete_hosts, complete_ports

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from logging.config import _HandlerConfiguration

    from xirvik.typing import TorrentInfo, TorrentTrackedFile

log = logging.getLogger(__name__)


def _ctrl_c_handler(_: int, __: Any) -> NoReturn:  # pragma: no cover
    msg = 'Signal raised.'
    raise SystemExit(msg)


@click.command(cls=command_with_config_file('config', 'add-torrents'))
@click.argument('directories',
                type=click.Path(exists=True, file_okay=False, path_type=Path),
                nargs=-1)
@click.option('--no-verify',
              default=False,
              is_flag=True,
              help='Disable TLS verification (not recommended)')
@click.option('--start-stopped', is_flag=True)
@click.option('-C', '--config', help='Configuration file')
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-d', '--debug', is_flag=True)
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-s', '--syslog', is_flag=True)
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
                      'xirvik': {
                          'handlers': handlers_tuple,
                          'propagate': False,
                      } if handlers_tuple else {}
                  })
    cache_dir = Path(realpath(Path('~/.cache/xirvik').expanduser()))
    cache_dir.mkdir(parents=True, exist_ok=True)
    post_url = f'https://{host:s}:{port:d}/rtorrent/php/addtorrent.php?'
    form_data = {}
    # rtorrent2/3 params
    # dir_edit - ?
    # tadd_label - Label for the torrents, more param: label=
    # torrent_file - Torrent file blob data
    if start_stopped:
        form_data['torrents_start_stopped'] = 'on'
    for d in (Path(x) for x in directories):
        for item in Path(d).iterdir():
            if not item.name.lower().endswith('.torrent'):
                continue
            item_inner = d / item
            # Workaround for surrogates not allowed error, rename the file
            prefix = f'{item_inner.name:s}-'
            with NamedTemporaryFile(prefix=prefix, suffix='.torrent', dir=cache_dir,
                                    delete=False) as w:
                w.write(item_inner.read_bytes())
                old = item_inner
            with Path(w.name).open('rb') as torrent_file:
                # Because the server does not understand filename*=UTF8 syntax
                # https://github.com/kennethreitz/requests/issues/2117
                # This is not a huge concern, as the API's "Get .torrent"
                # does not return the file with its original name either
                filename = unidecode(torrent_file.name)
                log.info('Uploading torrent %s (actual name: "%s").',
                         Path(item).name,
                         Path(filename).name)
                resp = requests.post(post_url,
                                     data=form_data,
                                     files={'torrent_file': (filename, torrent_file)},
                                     verify=not no_verify,
                                     timeout=30)
                if not resp.ok:
                    log.error('Error uploading %s.', old)
                    continue
                # Delete original only after successful upload
                log.debug('Deleting %s.', old)
                Path(old).unlink()


@click.command(cls=command_with_config_file('config', 'list-ftp-users'))
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
def list_ftp_users(
        host: str,
        port: int = 443,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """List FTP users."""  # noqa: DOC501
    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    r = requests.get(f'https://{host}:{port:d}/userpanel/index.php/ftp_users', timeout=30)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort from e
    content = Soup(r.text, 'html5lib').select('.gradeX td')
    click.echo(
        tabulate(((user.text, read_only.text == 'Yes', root_dir.text)
                  for user, read_only, root_dir, _ in (content[i:i + 4]
                                                       for i in range(0, len(content), 4))),
                 headers=('Username', 'Read-only', 'Root directory')))


@click.command(cls=command_with_config_file('config', 'add-ftp-user'))
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-r', '--root-directory', default='/')
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
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
    """Add an FTP user."""  # noqa: DOC501
    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    uri = (f'https://{host}:{port:d}/userpanel/index.php/'
           'ftp_users/add_user')
    root_dir = root_directory if root_directory.startswith('/') else f'/{root_directory}'
    # Setting read_only=yes does not appear to work
    r = requests.post(uri,
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


@click.command(cls=command_with_config_file('config', 'delete-ftp-user'))
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.argument('username')
def delete_ftp_user(
        host: str,
        username: str,
        port: int = 443,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """Delete an FTP user."""  # noqa: DOC501
    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    user = b64encode(username.encode()).decode()
    uri = (f'https://{host}:{port:d}/userpanel/index.php/ftp_users/'
           f'delete/{user}')
    r = requests.get(uri, timeout=30)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort from e


@click.command(cls=command_with_config_file('config', 'authorize-ip'))
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
def authorize_ip(
        host: str,
        port: int = 443,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """Authorise the current IP for access to the VM via SSH/VNC/RDP."""  # noqa: DOC501
    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    uri = (f'https://{host}:{port:d}/userpanel/index.php/virtual_machine/'
           'authorize_ip')
    r = requests.get(uri, timeout=30)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort from e


@click.command(cls=command_with_config_file('config', 'fix-rtorrent'))
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
def fix_rtorrent(
        host: str,
        port: int,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """
    Restart the rtorrent service in case ruTorrent cannot connect to it.

    Not guaranteed to fix anything!
    """  # noqa: DOC501
    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    log.info('No guarantees this will work!')
    uri = (f'https://{host}:{port:d}/userpanel/index.php/services/'
           'restart/rtorrent')
    r = requests.get(uri, timeout=30)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort from e


STATES_FOR_SORTING = {'finished', 'creation_date', 'state_changed'}


@click.command(cls=command_with_config_file('config', 'list-torrents'))
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-I', '--no-headers', is_flag=True)
@click.option('-F',
              '--table-format',
              type=click.Choice([*tabulate_formats, 'json']),
              default='plain')
@click.option('-S',
              '--sort',
              type=click.Choice(
                  ('name', 'hash', 'label', 'creation_date', 'state_changed', 'finished')))
@click.option('-R', '--reverse-order', is_flag=True)
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
    """List torrents in a given format."""  # noqa: DOC501
    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    min_tz_aware = datetime(MINYEAR, 1, 1, tzinfo=timezone.utc)

    def sorter(x: TorrentInfo) -> Any:
        assert sort is not None
        if ((val := getattr(x, sort if sort != 'label' else 'custom1', None)) is None
                and sort in STATES_FOR_SORTING):
            return min_tz_aware
        return val or ''

    torrents = cast('Iterator[TorrentInfo] | Sequence[TorrentInfo]',
                    ruTorrentClient(f'{host}:{port}').list_torrents())
    if sort:
        torrents = sorted(torrents, key=sorter)
    if reverse_order:
        torrents = reversed(list(torrents))
    if table_format in tabulate_formats:
        click.echo_via_pager(
            tabulate(((t.hash, t.name, t.custom1, t.finished) for t in torrents),
                     headers=() if no_headers else ('Hash', 'Name', 'Label', 'Finished'),
                     tablefmt=table_format))
    elif table_format == 'json':
        click.echo(
            json.dumps([{
                'hash': x.hash,
                'name': x.name,
                'label': x.custom1,
                'finished': x.finished.isoformat() if x.finished else None,
                'base_path': x.base_path
            } for x in torrents]))
    else:  # pragma no cover
        click.echo('Invalid table format specified.', err=True)
        raise click.Abort


@click.command(cls=command_with_config_file('config', 'list-files'))
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-I', '--no-headers', is_flag=True)
@click.option('-F',
              '--table-format',
              type=click.Choice([*tabulate_formats, 'json']),
              default='plain')
@click.option('-S', '--sort', type=click.Choice(('name', 'size_bytes', 'priority')), default='name')
@click.option('-R', '--reverse-order', is_flag=True)
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
    """List a torrent's files in a given format."""  # noqa: DOC501
    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    files = sorted(cast('Iterator[TorrentTrackedFile] | Sequence[TorrentTrackedFile]',
                        ruTorrentClient(f'{host}:{port}').list_files(hash)),
                   key=lambda x: getattr(x, sort))
    if reverse_order:
        files = list(reversed(list(files)))
    if table_format in tabulate_formats:
        click.echo_via_pager(
            tabulate(
                ((f.name, f.size_bytes, f.downloaded_pieces, f.number_of_pieces, str(f.priority_id))
                 for f in files),
                headers=() if no_headers else
                ('Name', 'Size', 'Downloaded Pieces', 'Number of Pieces', 'Priority ID'),
                tablefmt=table_format))
    elif table_format == 'json':
        click.echo(json.dumps([x._asdict() for x in files]))
    else:  # pragma no cover
        click.echo('Invalid table format specified.', err=True)
        raise click.Abort


def _resolve_single_file_torrent_path(info: TorrentInfo, filename: str) -> str:
    if not info.base_path.endswith(filename):
        return f'{info.base_path}/{filename}'
    return info.base_path


@click.command(cls=command_with_config_file('config', 'list-all-files'),
               help='list all tracked file paths.')
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
def list_all_files(
        host: str,
        port: int,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """List every tracked file."""
    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    client = ruTorrentClient(f'{host}:{port}')
    click.echo('Listing torrents ...', file=sys.stderr)
    with click.progressbar(list(client.list_torrents()), file=sys.stderr,
                           label='Getting file list') as progress_bar:
        info: TorrentInfo
        for info in progress_bar:
            files = list(client.list_files(info.hash))
            if len(files) == 1:
                click.echo(_resolve_single_file_torrent_path(info, files[0].name))
            else:
                for file in (f'{info.base_path}/{y.name}' for y in files):
                    click.echo(file)


@click.command(cls=command_with_config_file('config', 'list-untracked-files'),
               help='List untracked file paths.')
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-L',
              '--server-list-command',
              help=('This should be a command that outputs lines where each line is a '
                    'complete file path that matches the "torrents/<username>/..." output '
                    "from ruTorrent's API. An example using SSH:\n\n    "
                    "ssh name-of-server 'find /media/sf_hostshare -type f' | "
                    "sed -re 's|^/media/sf_hostshare|/torrents/username|g'"))
@click.option('-d', '--debug', is_flag=True)
def list_untracked_files(
        host: str,
        port: int,
        server_list_command: str,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False) -> None:
    """
    List all files on the server that are not tracked.

    All paths are fixed to be prefix with ``/downloads/`` instead of the old path
    ``/torrents/<username>``.
    """
    def fix_path(res: str) -> str:
        return re.sub(fr'^/torrents/{client.name}/', '/downloads/', res)

    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    click.echo('Getting server-side file list', file=sys.stderr)
    process = sp.run(  # noqa: S602
        server_list_command, shell=True, text=True, stdout=sp.PIPE, check=True)
    server_files = process.stdout.splitlines()
    client = ruTorrentClient(f'{host}:{port}')
    click.echo('Listing torrents ...', file=sys.stderr)
    with click.progressbar(list(client.list_torrents()), file=sys.stderr,
                           label='Getting file list') as progress_bar:
        info: TorrentInfo
        for info in progress_bar:
            log.debug('Torrent: %s', info.name)
            files = list(client.list_files(info.hash))
            assert len(files) >= 1, 'Zero files?'
            if len(files) == 1:
                res = fix_path(_resolve_single_file_torrent_path(info, files[0].name))
                log.debug('Single file: %s', res)
                try:
                    server_files.remove(res)
                except KeyError:  # pragma: no cover
                    log.debug('Unknown file  (%s): %s', info.name, res)
            else:
                for file in (fix_path(f'{info.base_path}/{y.name}') for y in files):
                    log.debug('File: %s', file)
                    try:
                        server_files.remove(file)
                    except KeyError:  # pragma: no cover
                        log.debug('Unknown file (%s): %s', info.name, file)
    for file in sorted(server_files):
        click.echo(file)


@click.command(cls=command_with_config_file('config', 'list-untracked-files'),
               help='List untracked file paths.')
@click.argument('untracked-filename', type=click.Path(exists=True, path_type=Path))
@click.argument('target', type=click.Path(path_type=Path))
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
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
    setup_logging(debug=debug, loggers={'fabric': {}, 'paramiko': {}, 'xirvik': {}})
    processed: set[str] = set()

    def get_lines() -> Iterator[str]:
        with untracked_filename.open(encoding='utf-8') as f:
            for file_or_dir in (f'/downloads/{"/".join(x.strip().split("/")[2:5])}' for x in f):
                if file_or_dir not in processed:
                    processed.add(file_or_dir)
                    yield file_or_dir

    def is_dir(client: Connection, path: str) -> bool:
        return bool(
            client.run(f'stat -c %F {quote(path)}', hide=True).stdout.strip() == 'directory')

    with Connection(host, port=port, user=username) as client:
        for file_or_dir in get_lines():
            out_file_or_dir = target / '/'.join(file_or_dir.split('/')[2:])
            out_file_or_dir.parent.mkdir(parents=True, exist_ok=True)
            src = f'{host}:{file_or_dir}{"/" if is_dir(client, file_or_dir) else ""}'
            sp.run(('rsync', '-e', f'ssh -p {port}', '--progress', '-lrtNEU', *(('-v') if debug else
                                                                                ()), src,
                    str(out_file_or_dir)),
                   check=True)
            log.info('Finished downloading `%s` to `%s`.', src, out_file_or_dir)
