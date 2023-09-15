#!/usr/bin/env python
"""Organise torrents based on labels assigned in ruTorrent."""
from os.path import expanduser
from time import sleep
from typing import Callable, Sequence

from loguru import logger
from requests.exceptions import HTTPError
import click

from xirvik.typing import TorrentInfo

from ..client import ruTorrentClient
from .util import command_with_config_file, common_options_and_arguments, setup_logging

PREFIX = '/downloads/{}'


def _base_path_check(username: str, completed_dir: str,
                     lower_label: bool) -> Callable[[TorrentInfo], bool]:
    def maybe_lower(x: str) -> str:
        if lower_label:
            return str.lower(x)
        return x

    def bpc(info: TorrentInfo) -> bool:
        return (not info.base_path.startswith(f'{PREFIX.format(completed_dir)}'
                                              f'/{maybe_lower(info.custom1 or "")}')
                # Old style paths
                and not info.base_path.startswith(f'/torrents/{username}/'))

    return bpc


def _key_check(info: TorrentInfo) -> bool:
    return not info.is_hash_checking and info.left_bytes == 0


@click.command(cls=command_with_config_file('config', 'move-by-label'))
@common_options_and_arguments
@click.option('-c',
              '--completed-dir',
              default='_completed',
              help='Top directory where moved torrent data will be placed')
@click.option('-t',
              '--sleep-time',
              default=10,
              type=int,
              help=('Time to sleep in seconds at certain times during this batch '
                    'of requests'))
@click.option('-l',
              '--lower-label',
              is_flag=True,
              help='Call lower() on labels used to make directory names')
@click.option('--ignore-labels', multiple=True, help='list of labels to ignore (case-sensitive)')
def main(host: str,
         ignore_labels: Sequence[str],
         netrc: str | None = None,
         username: str | None = None,
         password: str | None = None,
         completed_dir: str = '_completed',
         sleep_time: int = 10,
         lower_label: bool | None = None,
         max_retries: int = 10,
         debug: bool = False,
         backoff_factor: int = 1,
         config: str | None = None) -> None:
    """Move torrents according to labels assigned."""
    setup_logging(debug)
    logger.debug(f'Host: {host}')
    logger.debug(f'Configuration file: {config}')
    logger.debug(f'Use lowercase labels: {lower_label}')
    logger.debug(f'Ignoring labels: {", ".join(ignore_labels)}')
    client = ruTorrentClient(host,
                             name=username,
                             password=password,
                             max_retries=max_retries,
                             netrc_path=netrc or expanduser('~/.netrc'),
                             backoff_factor=backoff_factor)
    username = client.name
    assert username is not None
    try:
        torrents = client.list_torrents()
    except (ValueError, HTTPError) as e:
        logger.error('Connection failed on list_torrents() call')
        raise click.Abort() from e
    count = 0
    for info in (y for y in (x for x in torrents if _key_check(x))
                 if _base_path_check(username, completed_dir, lower_label or False)(y)):
        label = info.custom1
        if not label or label in ignore_labels:
            continue
        if lower_label:
            label = label.lower()
        move_to = f'{PREFIX.format(completed_dir)}/{label}'
        logger.info(f'Moving {info.name} from {info.base_path} to {move_to}/')
        client.move_torrent(info.hash, move_to)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(sleep_time)
