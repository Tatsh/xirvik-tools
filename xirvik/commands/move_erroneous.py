"""Move torrents in error state to another location."""
from time import sleep
from typing import Any, Final, Iterable, TypeVar

from loguru import logger
import click

from ..client import ruTorrentClient
from ..typing import TorrentInfo
from .util import command_with_config_file, common_options_and_arguments, setup_logging

__all__ = ('main',)

PREFIX: Final[str] = '/torrents/{}/_completed-not-active'
BAD_MESSAGES: Final[tuple[str, ...]] = (
    'unregistered torrent',
    "couldn't connect to server",
    'server returned nothing',
)
T = TypeVar('T')


def _has_one(look_for_list: Iterable[T], val: Iterable[T]) -> bool:
    return any(candidate in val for candidate in look_for_list)


def _should_process(x: TorrentInfo) -> bool:
    logger.debug(f'Name: "{x.name}", message: "{x.message}", '
                 f'is_hash_checking: {x.is_hash_checking}, '
                 f'left_bytes: {x.left_bytes}')
    return (_has_one(BAD_MESSAGES, x.message.lower()) and not x.is_hash_checking
            and x.left_bytes == 0 and bool(x.custom1))


def _make_move_to(prefix: str, label: str) -> str:
    return f'{prefix}/{label}'


@click.command(cls=command_with_config_file('config', 'move-erroneous'))
@common_options_and_arguments
@click.option('--sleep-time', type=int, default=10)
def main(
    host: str,
    netrc: str | None = None,
    username: str | None = None,
    password: str | None = None,
    sleep_time: int = 10,
    debug: bool = False,
    max_retries: int = 10,
    **kwargs: Any,
) -> None:
    """Move torrents in error state to another location."""
    setup_logging(debug)
    client = ruTorrentClient(host,
                             name=username,
                             password=password,
                             max_retries=max_retries,
                             netrc_path=netrc)
    prefix = PREFIX.format(client.name)
    to_delete: list[tuple[str, str]] = []
    items = [info for info in client.list_torrents() if _should_process(info)]
    count = 0
    for info in items:
        logger.info(f'Stopping {info.name}')
        client.stop(info.hash)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(sleep_time)
    count = 0
    for info in items:
        move_to = _make_move_to(prefix, info.custom1.lower())
        to_delete.append((info.hash, info.name))
        logger.info(f'Moving {info.name} to {move_to}/')
        client.move_torrent(info.hash, move_to)
        client.stop(info.hash)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(sleep_time)
    count = 0
    for hash_, name in to_delete:
        logger.info(f'Removing torrent "{name}" (without deleting data)')
        client.remove(hash_)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(sleep_time)
