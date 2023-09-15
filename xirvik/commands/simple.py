"""Mirror (copy data from remote to local) helper."""
from base64 import b64encode
from datetime import datetime
from logging.handlers import SysLogHandler
from os import listdir, makedirs, remove as rm
from os.path import basename, expanduser, isdir, join as path_join, realpath, splitext
from tempfile import NamedTemporaryFile
from typing import Any, Iterator, NoReturn, Sequence, cast
import json
import logging
import signal
import subprocess as sp
import sys

from bs4 import BeautifulSoup as Soup
from loguru import logger
from requests.exceptions import HTTPError
from tabulate import tabulate, tabulate_formats
from unidecode import unidecode
import click
import requests

from ..client import ruTorrentClient
from ..typing import TorrentInfo, TorrentTrackedFile
from .util import command_with_config_file, complete_hosts, complete_ports, setup_logging


def _ctrl_c_handler(_: int, __: Any) -> NoReturn:  # pragma: no cover
    """Used as a TERM signal handler. Arguments are ignored."""
    raise SystemExit('Signal raised')


@click.command(cls=command_with_config_file('config', 'add-torrents'))
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('--start-stopped', is_flag=True)
@click.option('-s', '--syslog', is_flag=True)
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.option('--no-verify',
              default=False,
              is_flag=True,
              help='Disable TLS verification (not recommended)')
@click.argument('directories', type=click.Path(exists=True, file_okay=False), nargs=-1)
def start_torrents(host: str,
                   directories: str,
                   port: int = 443,
                   debug: bool = False,
                   start_stopped: bool = False,
                   syslog: bool = False,
                   config: str | None = None,
                   no_verify: bool = False) -> None:
    """Uploads torrent files to the server."""
    signal.signal(signal.SIGINT, _ctrl_c_handler)
    setup_logging(debug)
    cache_dir = realpath(expanduser('~/.cache/xirvik'))
    if not isdir(cache_dir):
        makedirs(cache_dir)
    if syslog:  # pragma: no cover
        try:
            syslog_handle = SysLogHandler(address='/dev/log')
        except OSError:
            syslog_handle = SysLogHandler(address='/var/run/syslog',
                                          facility=SysLogHandler.LOG_USER)
            syslog_handle.ident = 'xirvik-start-torrents'
            logging.INFO = logging.WARNING
        logger.add(syslog_handle,
                   level='INFO' if not debug else 'DEBUG',
                   format='{name}[{process}]: {message}')
    post_url = f'https://{host:s}:{port:d}/rtorrent/php/addtorrent.php?'
    form_data = {}
    # rtorrent2/3 params
    # dir_edit - ?
    # tadd_label - Label for the torrents, more param: label=
    # torrent_file - Torrent file blob data
    if start_stopped:
        form_data['torrents_start_stopped'] = 'on'
    for d in directories:
        for item in listdir(d):
            if not item.lower().endswith('.torrent'):
                continue
            item_inner = path_join(d, item)
            # Workaround for surrogates not allowed error, rename the file
            prefix = f'{splitext(basename(item_inner))[0]:s}-'
            with NamedTemporaryFile(prefix=prefix, suffix='.torrent', dir=cache_dir,
                                    delete=False) as w:
                with open(item_inner, 'rb') as r:
                    w.write(r.read())
                old = item_inner
                item_inner = w.name
            with open(item_inner, 'rb') as torrent_file:
                # Because the server does not understand filename*=UTF8 syntax
                # https://github.com/kennethreitz/requests/issues/2117
                # This is not a huge concern, as the API's "Get .torrent"
                # does not return the file with its original name either
                filename = unidecode(torrent_file.name)
                logger.info(f'Uploading torrent {basename(item)} (actual '
                            f'name: "{basename(filename)}")')
                resp = requests.post(post_url,
                                     data=form_data,
                                     files=dict(torrent_file=(filename, torrent_file)),
                                     verify=not no_verify,
                                     timeout=30)
                if not resp.ok:
                    logger.error(f'Error uploading {old}')
                    continue
                # Delete original only after successful upload
                logger.debug(f'Deleting {old}')
                rm(old)


@click.command(cls=command_with_config_file('config', 'list-ftp-users'))
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
def list_ftp_users(host: str,
                   port: int = 443,
                   debug: bool = False,
                   config: str | None = None) -> None:
    """Lists FTP users."""
    setup_logging(debug)
    r = requests.get(f'https://{host}:{port:d}/userpanel/index.php/ftp_users', timeout=30)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort() from e
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
def add_ftp_user(host: str,
                 username: str,
                 password: str,
                 port: int = 443,
                 root_directory: str = '/',
                 debug: bool = False,
                 config: str | None = None) -> None:
    """Adds an FTP user."""
    setup_logging(debug)
    uri = (f'https://{host}:{port:d}/userpanel/index.php/'
           'ftp_users/add_user')
    root_dir = root_directory if root_directory.startswith('/') else f'/{root_directory}'
    # Setting read_only=yes does not appear to work
    r = requests.post(uri,
                      data=dict(username=username,
                                password_1=password,
                                root_folder=root_dir,
                                read_only='no'),
                      timeout=30)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort() from e


@click.command(cls=command_with_config_file('config', 'delete-ftp-user'))
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.argument('username')
def delete_ftp_user(host: str,
                    username: str,
                    port: int = 443,
                    debug: bool = False,
                    config: str | None = None) -> None:
    """Deletes an FTP user."""
    setup_logging(debug)
    user = b64encode(username.encode()).decode()
    uri = (f'https://{host}:{port:d}/userpanel/index.php/ftp_users/'
           f'delete/{user}')
    r = requests.get(uri, timeout=30)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort() from e


@click.command(cls=command_with_config_file('config', 'authorize-ip'))
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
def authorize_ip(host: str,
                 port: int = 443,
                 debug: bool = False,
                 config: str | None = None) -> None:
    """Authorises the current IP for access to the VM via SSH/VNC/RDP."""
    setup_logging(debug)
    uri = (f'https://{host}:{port:d}/userpanel/index.php/virtual_machine/'
           'authorize_ip')
    r = requests.get(uri, timeout=30)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort() from e


@click.command(cls=command_with_config_file('config', 'fix-rtorrent'))
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
def fix_rtorrent(host: str, port: int, debug: bool = False, config: str | None = None) -> None:
    """
    Restarts the rtorrent service in case ruTorrent cannot connect to it. Not
    guaranteed to fix anything!
    """
    setup_logging(debug)
    logger.info('No guarantees this will work!')
    uri = (f'https://{host}:{port:d}/userpanel/index.php/services/'
           'restart/rtorrent')
    r = requests.get(uri, timeout=30)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort() from e


STATES_FOR_SORTING = set(('finished', 'creation_date', 'state_changed'))


@click.command(cls=command_with_config_file('config', 'list-torrents'))
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-I', '--no-headers', is_flag=True)
@click.option('-F',
              '--table-format',
              type=click.Choice(tabulate_formats + ['json']),
              default='plain')
@click.option('-S',
              '--sort',
              type=click.Choice(
                  ('name', 'hash', 'label', 'creation_date', 'state_changed', 'finished')))
@click.option('-R', '--reverse-order', is_flag=True)
def list_torrents(host: str,
                  port: int,
                  debug: bool = False,
                  config: str | None = None,
                  no_headers: bool = False,
                  table_format: str = 'plain',
                  sort: str | None = None,
                  reverse_order: bool | None = None) -> None:
    """list torrents in a given format."""
    def sorter(x: TorrentInfo) -> Any:
        assert sort is not None
        if ((val := getattr(x, sort if sort != 'label' else 'custom1', None)) is None
                and sort in STATES_FOR_SORTING):
            return datetime.min
        return val or ''

    setup_logging(debug)
    torrents = cast(Iterator[TorrentInfo] | Sequence[TorrentInfo],
                    ruTorrentClient(host).list_torrents())
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
            json.dumps([
                dict(hash=x.hash,
                     name=x.name,
                     label=x.custom1,
                     finished=x.finished.isoformat() if x.finished else None,
                     base_path=x.base_path) for x in torrents
            ]))
    else:  # pragma no cover
        raise click.Abort('Invalid table format specified')


@click.command(cls=command_with_config_file('config', 'list-files'))
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.option('-p', '--port', type=int, default=443, shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-I', '--no-headers', is_flag=True)
@click.option('-F',
              '--table-format',
              type=click.Choice(tabulate_formats + ['json']),
              default='plain')
@click.option('-S', '--sort', type=click.Choice(('name', 'size_bytes', 'priority')), default='name')
@click.option('-R', '--reverse-order', is_flag=True)
@click.argument('hash')
def list_files(hash: str,
               host: str,
               port: int,
               debug: bool = False,
               config: str | None = None,
               no_headers: bool = False,
               table_format: str = 'plain',
               sort: str = 'name',
               reverse_order: bool | None = None) -> None:
    """list a torrent's files in a given format."""
    setup_logging(debug)
    files = sorted(cast(Iterator[TorrentTrackedFile] | Sequence[TorrentTrackedFile],
                        ruTorrentClient(host).list_files(hash)),
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
        raise click.Abort('Invalid table format specified')


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
def list_all_files(host: str, port: int, debug: bool = False, config: str | None = None) -> None:
    """list every tracked file."""
    setup_logging(debug)
    client = ruTorrentClient(host)
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
               help='list untracked file paths.')
@click.option('-H', '--host', help='Xirvik host (without protocol)', shell_complete=complete_hosts)
@click.option('-L',
              '--server-list-command',
              help=('This should be a command that outputs lines where each line is a '
                    'complete file path that matches the "torrents/<username>/..." output '
                    'from ruTorrent\'s API. An example using SSH:\n\n    '
                    "ssh name-of-server 'find /media/sf_hostshare -type f' | "
                    "sed -re 's|^/media/sf_hostshare|/torrents/username|g'"))
@click.option('-d', '--debug', is_flag=True)
def list_untracked_files(host: str,
                         server_list_command: str,
                         debug: bool = False,
                         config: str | None = None) -> None:
    """
    list all files on the server that are not tracked.

    Parameters
    ==========
    host : str
        Hostname.

    server_list_command : str
        This should be a command that outputs lines where each line is a
        complete file path that matches the ``torrents/<username>/...`` output
        from ruTorrent's API. An example using SSH would be:

            ``ssh name-of-server 'find /media/sf_hostshare -type f' |
              sed -re 's|^/media/sf_hostshare|/torrents/username|g'``

    debug : bool
        Enable debugging output.
    """
    setup_logging(debug)
    client = ruTorrentClient(host)
    click.echo('Listing torrents ...', file=sys.stderr)
    tracked_files = cast(set[str], set())
    with click.progressbar(list(client.list_torrents()), file=sys.stderr,
                           label='Getting file list') as progress_bar:
        info: TorrentInfo
        for info in progress_bar:
            files = list(client.list_files(info.hash))
            if len(files) == 1:
                tracked_files.add(_resolve_single_file_torrent_path(info, files[0].name))
            else:
                for file in (f'{info.base_path}/{y.name}' for y in files):
                    tracked_files.add(file)
    click.echo('Getting server-side file list', file=sys.stderr)
    with sp.Popen(server_list_command, shell=True, text=True, stdout=sp.PIPE) as process:
        assert process.stdout is not None
        while (line := process.stdout.readline().strip()):
            if line not in tracked_files:
                click.echo(line)
