"""Mirror (copy data from remote to local) helper."""
from base64 import b64encode
from logging.handlers import SysLogHandler
from netrc import netrc
from os import close as close_fd, listdir, makedirs, remove as rm
from os.path import (basename, expanduser, isdir, join as path_join, realpath,
                     splitext)
from tempfile import mkstemp
import logging
import signal
import socket
import sys

from requests.exceptions import HTTPError
from unidecode import unidecode
import click
import requests

from loguru import logger
from ..util import ctrl_c_handler
from .util import complete_hosts, complete_ports, setup_log_intercept_handler


@click.command()
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('--start-stopped', is_flag=True)
@click.option('-s', '--syslog', is_flag=True)
@click.argument('host', shell_complete=complete_hosts)
@click.argument('directories',
                type=click.Path(exists=True, file_okay=False),
                nargs=-1)
def start_torrents(host: str,
                   directories: str,
                   port: int = 443,
                   debug: bool = False,
                   start_stopped: bool = False,
                   syslog: bool = False) -> None:
    """Uploads torrent files to the server."""
    signal.signal(signal.SIGINT, ctrl_c_handler)
    cache_dir = realpath(expanduser('~/.cache/xirvik'))
    if not isdir(cache_dir):
        makedirs(cache_dir)
    if debug:
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.configure(handlers=[dict(sink=sys.stdout, format='{message}')])
        logger.level('INFO')
    if syslog:
        try:
            syslogh = SysLogHandler(address='/dev/log')
        except (OSError, socket.error):
            syslogh = SysLogHandler(address='/var/run/syslog',
                                    facility=SysLogHandler.LOG_USER)
            syslogh.ident = 'xirvik-start-torrents'
            logging.INFO = logging.WARNING
        logger.add(syslogh,
                   level='INFO' if not debug else 'DEBUG',
                   format='{name}[{process}]: {message}')
    user_pass = netrc(expanduser('~/.netrc')).authenticators(host)
    if not user_pass:
        logger.error(f'Cannot find host {host} in netrc.')
        sys.exit(1)
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
            prefix = '{n:s}-'.format(n=splitext(basename(item))[0])
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
                files = dict(torrent_file=(
                    filename,
                    torrent_file,
                ))
                try:
                    logger.info(f'Uploading torrent {basename(item)} (actual '
                                f'name: "{basename(filename)}")')
                except OSError:
                    pass
                resp = requests.post(post_url, data=form_data, files=files)
                try:
                    resp.raise_for_status()
                except HTTPError:
                    logger.exception('HTTP error')
                # Delete original only after successful upload
                logger.debug(f'Deleting {old}')
                rm(old)


@click.command()
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.option('-r', '--root-directory', default='/')
@click.argument('host', shell_complete=complete_hosts)
@click.argument('username')
@click.argument('password')
def add_ftp_user(host: str,
                 username: str,
                 password: str,
                 port: int = 443,
                 root_directory: str = '/',
                 debug: bool = False) -> int:
    """Adds an FTP user."""
    if debug:
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.level('INFO')
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
        logger.exception(e)
        return 1
    return 0


@click.command()
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.argument('host', shell_complete=complete_hosts)
@click.argument('username')
def delete_ftp_user(host: str,
                    username: str,
                    port: int = 443,
                    debug: bool = False) -> int:
    """Deletes an FTP user."""
    if debug:
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.level('INFO')
    user = b64encode(username.encode()).decode()
    uri = (f'https://{host}:{port:d}/userpanel/index.php/ftp_users/'
           f'delete/{user}')
    r = requests.get(uri)
    try:
        r.raise_for_status()
    except HTTPError:
        logger.exception('HTTP error')
        return 1
    return 0


@click.command()
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
@click.argument('host', shell_complete=complete_hosts)
def authorize_ip(host: str, port: int = 443, debug: bool = False) -> int:
    """Authorises the current IP for access to the VM via SSH/VNC/RDP."""
    if debug:
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.level('INFO')
    uri = (f'https://{host}:{port:d}/userpanel/index.php/virtual_machine/'
           'authorize_ip')
    r = requests.get(uri)
    try:
        r.raise_for_status()
    except HTTPError:
        logger.exception('HTTP error')
        return 1
    return 0


@click.command()
@click.argument('host', shell_complete=complete_hosts)
@click.option('-p',
              '--port',
              type=int,
              default=443,
              shell_complete=complete_ports)
@click.option('-d', '--debug', is_flag=True)
def fix_rtorrent(host: str, port: int, debug: bool = False) -> int:
    """
    Restarts the rtorrent service in case ruTorrent cannot connect to it. Not
    guaranteed to fix anything!
    """
    if debug:
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.level('INFO')
    logger.info('No guarantees this will work!')
    uri = (f'https://{host}:{port:d}/userpanel/index.php/services/'
           'restart/rtorrent')
    r = requests.get(uri)
    try:
        r.raise_for_status()
    except HTTPError:
        logger.exception('HTTP error')
        return 1
    return 0
