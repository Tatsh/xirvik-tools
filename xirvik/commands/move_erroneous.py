"""Move torrents in error state to another location."""
from time import sleep
from typing import Iterable, List, Tuple, TypeVar, cast
import sys

from typing_extensions import Final
import argcomplete

from ..client import ruTorrentClient
from ..typing import TorrentDict
from .util import common_parser, setup_logging_stdout

__all__ = ("main", )

PREFIX: Final = '/torrents/{}/_completed-not-active'
BAD_MESSAGES: Final = (
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


def _should_process(x: TorrentDict) -> bool:
    return (_has_one(BAD_MESSAGES, x['message']) and not x['is_hash_checking']
            and x['left_bytes'] == 0)


def _make_move_to(prefix: str, label: str) -> str:
    return '{}/{}'.format(prefix, label)


def main() -> int:
    """Move torrents in error state to another location."""
    parser: Final = common_parser()
    parser.add_argument('-a', '--ignore-ratio', action='store_true')
    parser.add_argument('-t', '--sleep-time', default=10, type=int)
    argcomplete.autocomplete(parser)
    args: Final = parser.parse_args()
    log: Final = setup_logging_stdout(verbose=args.verbose)
    client: Final = ruTorrentClient(args.host[0],
                                    name=args.username,
                                    password=args.password,
                                    max_retries=args.max_retries,
                                    netrc_path=args.netrc)
    prefix: Final = PREFIX.format(args.username)
    to_delete: List[Tuple[str, str]] = []
    items: Final = [(hash_, cast(TorrentDict, info))
                    for hash_, info in client.list_torrents_dict().items()
                    if _should_process(cast(TorrentDict, info))]
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
