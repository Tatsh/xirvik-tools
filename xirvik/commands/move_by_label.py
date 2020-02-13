#!/usr/bin/env python
"""Organise torrents based on labels assigned in ruTorrent."""
from time import sleep
from typing import Any, Callable, Dict, Mapping, Tuple, Union
import sys

from requests.exceptions import HTTPError
import argcomplete

from ..client import ruTorrentClient
from .util import common_parser, setup_logging_stdout

PREFIX = '/torrents/{}/_completed'


def _base_path_check(
        username: str) -> Callable[[Tuple[Any, Mapping[str, str]]], bool]:
    def bpc(hash_info: Tuple[Any, Mapping[str, str]]) -> bool:
        _, info = hash_info
        move_to = '{}/{}'.format(PREFIX.format(username),
                                 str.lower(info['custom1']))
        return not info['base_path'].startswith(move_to)

    return bpc


def _key_check(hash_info: Tuple[Any, Mapping[str, Union[bool, int]]]) -> bool:
    _, info = hash_info
    return not info['is_hash_checking'] and info['left_bytes'] == 0


def main() -> int:
    """Entry point."""
    parser = common_parser()
    parser.add_argument(
        '-c',
        '--completed-dir',
        default='_completed',
        help='Top directory where moved torrent data will be placed')
    parser.add_argument(
        '-t',
        '--sleep-time',
        default=10,
        type=int,
        help=('Time to sleep in seconds at certain times during this batch '
              'of requests'))
    parser.add_argument(
        '-l',
        '--lower-label',
        action='store_true',
        help='Call lower() on labels used to make directory names')
    parser.add_argument('--ignore-labels',
                        nargs='+',
                        default=[],
                        help='List of label names to ignore')
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    log = setup_logging_stdout(verbose=args.verbose)
    assert log is not None
    client = ruTorrentClient(args.host[0],
                             name=args.username,
                             password=args.password,
                             max_retries=args.max_retries,
                             netrc_path=args.netrc)
    username = client.name
    try:
        torrents = list(client.list_torrents_dict().items())
    except (ValueError, HTTPError):
        log.error('Connection failed on list_torrents() call')
        return 1
    count = 0
    assert username is not None
    hash_: str
    info: Dict[str, str]
    for hash_, info in list(
            filter(_base_path_check(username), filter(_key_check, torrents))):
        label = info['custom1']
        if label in args.ignore_labels:
            continue
        if args.lower_label:
            label = label.lower()
        move_to = '{}/{}'.format(PREFIX.format(username), label)
        log.info('Moving %s to %s/', info['name'], move_to)
        client.move_torrent(hash_, move_to)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(args.sleep_time)
    return 0


if __name__ == '__main__':
    sys.exit(main())
