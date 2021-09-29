"""Mirror (copy data from remote to local) helper."""
from base64 import b64encode
from logging.handlers import SysLogHandler
from os import close as close_fd, listdir, makedirs, remove as rm
from os.path import (basename, expanduser, isdir, join as path_join, realpath,
                     splitext)
from tempfile import mkstemp
from typing import Any, NoReturn, Optional
import logging
import signal
import socket
import sys

from loguru import logger
from requests.exceptions import HTTPError
from unidecode import unidecode
import click
import requests

from .util import (command_with_config_file, complete_hosts, complete_ports,
                   setup_log_intercept_handler)


def _ctrl_c_handler(_: int, __: Any) -> NoReturn:  # pragma: no cover
    """Used as a TERM signal handler. Arguments are ignored."""
    raise SystemExit('Signal raised')


# pylint: disable=unused-argument


@click.command(cls=command_with_config_file('config', 'add-torrents'))
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('--start-stopped', is_flag=True)
@click.option('-s', '--syslog', is_flag=True)
@click.option('-H',
              '--host',
              help='Xirvik host (without protocol)',
              shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.argument('directories',
                type=click.Path(exists=True, file_okay=False),
                nargs=-1)
def start_torrents(host: str,
                   directories: str,
                   port: int = 443,
                   debug: bool = False,
                   start_stopped: bool = False,
                   syslog: bool = False,
                   config: Optional[str] = None) -> None:
    """Uploads torrent files to the server."""
    signal.signal(signal.SIGINT, _ctrl_c_handler)
    cache_dir = realpath(expanduser('~/.cache/xirvik'))
    if not isdir(cache_dir):
        makedirs(cache_dir)
    if debug:  # pragma: no cover
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.configure(handlers=[dict(sink=sys.stdout, format='{message}')])
    if syslog:  # pragma: no cover
        try:
            syslog_handle = SysLogHandler(address='/dev/log')
        except (OSError, socket.error):
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
            item = path_join(d, item)
            # Workaround for surrogates not allowed error, rename the file
            prefix = f'{splitext(basename(item))[0]:s}-'
            fd, name = mkstemp(dir=cache_dir, prefix=prefix, suffix='.torrent')
            close_fd(fd)
            with open(name, 'wb') as w:
                with open(item, 'rb') as r:
                    w.write(r.read())
            old = item
            item = name
            with open(item, 'rb') as torrent_file:
                # Because the server does not understand filename*=UTF8 syntax
                # https://github.com/kennethreitz/requests/issues/2117
                # This is not a huge concern, as the API's "Get .torrent" does
                # not return the file with its original name either
                filename = unidecode(torrent_file.name)
                files = dict(torrent_file=(filename, torrent_file))
                logger.info(f'Uploading torrent {basename(item)} (actual '
                            f'name: "{basename(filename)}")')
                resp = requests.post(post_url, data=form_data, files=files)
                if not resp.ok:
                    logger.error(f'Error uploading {old}')
                    continue
                # Delete original only after successful upload
                logger.debug(f'Deleting {old}')
                rm(old)


@click.command(cls=command_with_config_file('config', 'add-ftp-user'))
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-r', '--root-directory', default='/')
@click.option('-H',
              '--host',
              help='Xirvik host (without protocol)',
              shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.argument('username')
@click.argument('password')
def add_ftp_user(host: str,
                 username: str,
                 password: str,
                 port: int = 443,
                 root_directory: str = '/',
                 debug: bool = False,
                 config: Optional[str] = None) -> None:
    """Adds an FTP user."""
    if debug:  # pragma: no cover
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.configure(handlers=[dict(level='INFO', sink=sys.stderr)])
    uri = (f'https://{host}:{port:d}/userpanel/index.php/'
           'ftp_users/add_user')
    rootdir = root_directory if root_directory.startswith(
        '/') else f'/{root_directory}'
    # Setting read_only=yes does not appear to work
    r = requests.post(uri,
                      data=dict(username=username,
                                password_1=password,
                                root_folder=rootdir,
                                read_only='no'))
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort() from e


@click.command(cls=command_with_config_file('config', 'delete-ftp-user'))
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-H',
              '--host',
              help='Xirvik host (without protocol)',
              shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.argument('username')
def delete_ftp_user(host: str,
                    username: str,
                    port: int = 443,
                    debug: bool = False,
                    config: Optional[str] = None) -> None:
    """Deletes an FTP user."""
    if debug:  # pragma: no cover
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.configure(handlers=[dict(level='INFO', sink=sys.stderr)])
    user = b64encode(username.encode()).decode()
    uri = (f'https://{host}:{port:d}/userpanel/index.php/ftp_users/'
           f'delete/{user}')
    r = requests.get(uri)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort() from e


@click.command(cls=command_with_config_file('config', 'authorize-ip'))
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-H',
              '--host',
              help='Xirvik host (without protocol)',
              shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
def authorize_ip(host: str,
                 port: int = 443,
                 debug: bool = False,
                 config: Optional[str] = None) -> None:
    """Authorises the current IP for access to the VM via SSH/VNC/RDP."""
    if debug:  # pragma: no cover
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.configure(handlers=[dict(level='INFO', sink=sys.stderr)])
    uri = (f'https://{host}:{port:d}/userpanel/index.php/virtual_machine/'
           'authorize_ip')
    r = requests.get(uri)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort() from e


@click.command(cls=command_with_config_file('config', 'fix-rtorrent'))
@click.option('-H',
              '--host',
              help='Xirvik host (without protocol)',
              shell_complete=complete_hosts)
@click.option('-C', '--config', help='Configuration file')
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
def fix_rtorrent(host: str,
                 port: int,
                 debug: bool = False,
                 config: Optional[str] = None) -> None:
    """
    Restarts the rtorrent service in case ruTorrent cannot connect to it. Not
    guaranteed to fix anything!
    """
    if debug:  # pragma: no cover
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.configure(handlers=[dict(level='INFO', sink=sys.stderr)])
    logger.info('No guarantees this will work!')
    uri = (f'https://{host}:{port:d}/userpanel/index.php/services/'
           'restart/rtorrent')
    r = requests.get(uri)
    try:
        r.raise_for_status()
    except HTTPError as e:
        raise click.Abort() from e
