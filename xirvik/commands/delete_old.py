#!/usr/bin/env python
"""
Deletes old torrents based on specified criteria.
"""
from datetime import datetime, timedelta
from time import sleep
from typing import Any, Callable, Dict, Optional, Tuple, Union
import logging
import sys
import xmlrpc.client as xmlrpc

from requests.exceptions import HTTPError
import argcomplete

from ..client import ruTorrentClient
from .util import common_parser, setup_logging_stdout

TestCallable = Callable[[Dict[str, Any], logging.Logger], Tuple[str, bool]]
TestsDict = Dict[str, Tuple[bool, TestCallable]]


def _test_date_cb(days: int = 14) -> TestCallable:
    def test_date(info: Dict[str, datetime],
                  log: logging.Logger) -> Tuple[str, bool]:
        cond1 = info.get('creation_date')
        cond2 = info.get('state_changed')
        expect = datetime.now() - timedelta(days=days)
        log = setup_logging_stdout()
        log.debug('creation date: %s', cond1)
        log.debug('state changed: %s', cond2)
        log.debug('%s <= %s or', cond1, expect)
        log.debug('    %s <= %s', cond2, expect)
        return (
            'over 14 days seeded',
            bool((cond1 and cond1 <= expect) or (cond2 and cond2 <= expect)),
        )

    return test_date


def _test_ratio(info: Dict[str, float],
                log: logging.Logger) -> Tuple[str, bool]:
    log.debug('ratio: %.2f', info.get('ratio', 0.0))
    return 'ratio >= 1', info.get('ratio', 0.0) >= 1


def _test_ignore(_info: Any) -> Tuple[str, bool]:
    return 'ignoring criteria', True


def main() -> int:
    """Entry point."""
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
        ratio=(args.ignore_ratio, _test_ratio),
        date=(args.ignore_date, _test_date_cb(args.days)),
    )
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
            reason, can_delete = test(info, log)
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
            except xmlrpc.Fault as e:
                log.exception(e)
                sleep_time = args.backoff_factor * (2**(attempts - 1))
                sleep(sleep_time)
            else:
                sleep(args.sleep_time)
                break
    return 0


if __name__ == '__main__':
    sys.exit(main())
