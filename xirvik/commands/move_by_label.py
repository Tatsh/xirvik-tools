#!/usr/bin/env python
"""Organise torrents based on labels assigned in ruTorrent."""
from os.path import expanduser
from time import sleep
from typing import Any, Callable, Optional, Sequence, Tuple

from loguru import logger
from requests.exceptions import HTTPError
import click

from xirvik.typing import TorrentDict

from ..client import ruTorrentClient
from .util import common_options_and_arguments, setup_log_intercept_handler

PREFIX = '/torrents/{}/{}'


def _base_path_check(
        username: str, completed_dir: str,
        lower_label: bool) -> Callable[[Tuple[Any, TorrentDict]], bool]:
    def maybe_lower(x: str) -> str:
        if lower_label:
            return str.lower(x)
        return x

    def bpc(hash_info: Tuple[Any, TorrentDict]) -> bool:
        _, info = hash_info
        return not info['base_path'].startswith(
            f'{PREFIX.format(username, completed_dir)}'
            f'/{maybe_lower(info["custom1"] or "")}')

    return bpc


def _key_check(hash_info: Tuple[Any, TorrentDict]) -> bool:
    _, info = hash_info
    return not info['is_hash_checking'] and info['left_bytes'] == 0


@click.command()
@common_options_and_arguments
@click.option('-c',
              '--completed-dir',
              default='_completed',
              help='Top directory where moved torrent data will be placed')
@click.option(
    '-t',
    '--sleep-time',
    default=10,
    type=int,
    help=('Time to sleep in seconds at certain times during this batch '
          'of requests'))
@click.option('-l',
              '--lower-label',
              is_flag=True,
              help='Call lower() on labels used to make directory names')
@click.option('--ignore-labels',
              multiple=True,
              default=[],
              help='List of labels to ignore (case-sensitive)')
def main(  # pylint: disable=too-many-arguments
        host: str,
        ignore_labels: Sequence[str],
        netrc: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        completed_dir: str = '_completed',
        sleep_time: int = 10,
        lower_label: bool = False,
        max_retries: int = 10,
        debug: bool = False,
        backoff_factor: int = 1) -> None:
    """Move torrents according to labels assigned."""
    if debug:  # pragma: no cover
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.level('INFO')
    client = ruTorrentClient(host,
                             name=username,
                             password=password,
                             max_retries=max_retries,
                             netrc_path=netrc or expanduser('~/.netrc'),
                             backoff_factor=backoff_factor)
    username = client.name
    assert username is not None
    try:
        torrents = client.list_torrents_dict()
    except (ValueError, HTTPError) as e:
        logger.error('Connection failed on list_torrents() call')
        raise click.Abort() from e
    count = 0
    for hash_, info in (
            y for y in (x for x in torrents.items() if _key_check(x))
            if _base_path_check(username, completed_dir, lower_label)(y)):
        label = info['custom1']
        if not label or label in ignore_labels:
            continue
        if lower_label:
            label = label.lower()
        move_to = f'{PREFIX.format(username, completed_dir)}/{label}'
        logger.info(f'Moving {info["name"]} to {move_to}/')
        client.move_torrent(hash_, move_to)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(sleep_time)
