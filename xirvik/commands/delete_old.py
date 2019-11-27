#!/usr/bin/env python
from datetime import datetime, timedelta
from time import sleep
from typing import Any, Callable, Dict, Optional, Tuple, Union
import logging
import sys

from requests.exceptions import HTTPError
import argcomplete

from ..client import ruTorrentClient
from .util import setup_logging_stdout, common_parser

TestsDict = Dict[str,
                 Tuple[bool, Callable[[Dict[str, Any]], Tuple[str, bool]]]]
log: Optional[logging.Logger] = None


def test_date_cb(days: int = 14
                 ) -> Callable[[Dict[str, datetime]], Tuple[str, bool]]:
    def test_date(info: Dict[str, datetime]) -> Tuple[str, bool]:
        sc = info.get('creation_date')
        sc2 = info.get('state_changed')
        expect = datetime.now() - timedelta(days=days)
        assert log is not None
        log.debug('creation date: %s', sc)
        log.debug('state changed: %s', sc2)
        log.debug('%s <= %s or', sc, expect)
        log.debug('    %s <= %s', sc2, expect)
        return (
            'over 14 days seeded',
            bool((sc and sc <= expect) or (sc2 and sc2 <= expect)),
        )

    return test_date


def test_ratio(info: Dict[str, float]) -> Tuple[str, bool]:
    assert log is not None
    log.debug('ratio: %.2f', info.get('ratio', 0.0))
    return 'ratio >= 1', info.get('ratio', 0.0) >= 1


def test_ignore(info: Dict[str, Any]) -> Tuple[str, bool]:
    return 'ignoring criteria', True


def main() -> int:
    global log
    parser = common_parser()
    parser.add_argument('-a', '--ignore-ratio', action='store_true')
    parser.add_argument('-D', '--ignore-date', action='store_true')
    parser.add_argument('-y', '--dry-run', action='store_true')
    parser.add_argument('--max-attempts', type=int, default=3)
    parser.add_argument('--label')
    parser.add_argument('--sleep-time', type=int, default=10)
    parser.add_argument('--days', type=int, default=14)
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    log = setup_logging_stdout(verbose=args.verbose)
    assert log is not None

    client = ruTorrentClient(args.host[0],
                             name=args.username,
                             password=args.password,
                             max_retries=args.max_retries,
                             netrc_path=args.netrc)
    try:
        torrents = client.list_torrents_dict().items()
    except HTTPError:
        log.error('Connection failed on list_torrents() call', file=sys.stderr)
        return 1
    tests: TestsDict = dict(
        ratio=(args.ignore_ratio, test_ratio),
        date=(args.ignore_date, test_date_cb(args.days)),
    )

    hash_: str
    info: Dict[str, Union[int, str, bool]]
    for hash_, info in torrents:
        if info['left_bytes'] != 0 or info['custom1'] != args.label:
            continue

        reason: Optional[str] = None
        can_delete: bool = False
        for key, (can_ignore, test) in tests.items():
            if can_ignore:
                can_delete = True
                reason = f'ignoring {key}'
                break
            reason, can_delete = test(info)
            if can_delete:
                break

        if not can_delete:
            log.info('Cannot delete %s', info['name'])
            continue

        if args.dry_run:
            log.info('Would delete %s, reason: %s', info['name'], reason)
            continue
        else:
            log.info('Deleting %s, reason: %s', info['name'], reason)

        attempts = 0
        while attempts < args.max_attempts:
            attempts += 1
            try:
                client.delete(hash_)
            except Exception as e:
                log.exception(e)
                sleep_time = args.backoff_factor * (2**(attempts - 1))
                sleep(sleep_time)
            else:
                sleep(args.sleep_time)
                break

    return 0


if __name__ == '__main__':
    sys.exit(main())
