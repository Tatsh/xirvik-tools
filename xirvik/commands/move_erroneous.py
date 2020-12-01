"""Move torrents in error state to another location."""
from time import sleep
from typing import Iterable, List, Tuple, TypeVar, cast
import argparse
import logging
import sys

from typing_extensions import Final
import argcomplete

from ..client import ruTorrentClient
from ..typing import TorrentDict
from .util import common_parser, setup_logging_stdout

__all__ = ('main',)

PREFIX: Final[str] = '/torrents/{}/_completed-not-active'
BAD_MESSAGES: Final[Tuple[str, ...]] = (
    'unregistered torrent',
    "couldn't connect to server",
    'server returned nothing',
)
T = TypeVar('T')


def _has_one(look_for_list: Iterable[T], val: Iterable[T]) -> bool:
    for candidate in look_for_list:
        if candidate in val:
            return True
    return False


def _should_process(x: TorrentDict, log: logging.Logger) -> bool:
    log.debug(
        'Name: "%s", message: "%s", is_hash_checking: %s, left_bytes: %d',
        x['name'], x['message'], x['is_hash_checking'], x['left_bytes'])
    return (_has_one(BAD_MESSAGES, x['message'].lower())
            and not x['is_hash_checking'] and x['left_bytes'] == 0)


def _make_move_to(prefix: str, label: str) -> str:
    return '{}/{}'.format(prefix, label)


class Namespace(argparse.Namespace):
    """Arguments."""
    ignore_ratio: bool
    sleep_time: int
    verbose: bool


def main() -> int:
    """Move torrents in error state to another location."""
    parser: Final[argparse.ArgumentParser] = common_parser()
    parser.add_argument('-a', '--ignore-ratio', action='store_true')
    parser.add_argument('-t', '--sleep-time', default=10, type=int)
    argcomplete.autocomplete(parser)
    args: Final[Namespace] = cast(Namespace, parser.parse_args())
    log: Final[logging.Logger] = setup_logging_stdout(verbose=args.verbose)
    client: Final[ruTorrentClient] = ruTorrentClient(
        args.host[0],
        name=args.username,
        password=args.password,
        max_retries=args.max_retries,
        netrc_path=args.netrc)
    prefix: Final[str] = PREFIX.format(client.name)
    to_delete: List[Tuple[str, str]] = []
    items: Final[List[Tuple[str, TorrentDict]]] = [
        (hash_, info) for hash_, info in client.list_torrents_dict().items()
        if _should_process(info, log)
    ]
    count = 0
    for hash_, info in items:
        log.info('Stopping %s', info['name'])
        client.stop(hash_)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(args.sleep_time)
    count = 0
    for hash_, info in items:
        move_to = _make_move_to(prefix, info['custom1'].lower())
        to_delete.append((hash_, info['name']))
        log.info('Moving %s to %s/', info['name'], move_to)
        client.move_torrent(hash_, move_to)
        client.stop(hash_)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(args.sleep_time)
    count = 0
    for hash_, name in to_delete:
        log.info('Removing torrent "%s" (without deleting data)', name)
        client.remove(hash_)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(args.sleep_time)
    return 0


if __name__ == '__main__':
    sys.exit(main())
