#!/usr/bin/env python
"""
Deletes old torrents based on specified criteria.
"""
from datetime import datetime, timedelta
from os.path import expanduser
from time import sleep
from typing import Callable, Dict, Optional, Tuple, cast
import xmlrpc.client as xmlrpc

from loguru import logger
from requests.exceptions import HTTPError
import click

from xirvik.typing import TorrentDict

from ..client import ruTorrentClient
from .util import common_options_and_arguments, setup_log_intercept_handler

TestCallable = Callable[[TorrentDict], Tuple[str, bool]]
TestsDict = Dict[str, Tuple[bool, TestCallable]]


def _test_date_cb(days: int = 14) -> TestCallable:
    def test_date(info: TorrentDict) -> Tuple[str, bool]:
        cond1 = info.get('creation_date')
        cond2 = info.get('state_changed')
        expect = datetime.now() - timedelta(days=days)
        logger.debug(f'creation date: {cond1}')
        logger.debug(f'state changed: {cond2}')
        logger.debug(f'{cond1} <= {expect} or')
        logger.debug(f'    {cond2} <= {expect}')
        return (
            'over 14 days seeded',
            bool((cond1 and cond1 <= expect) or (cond2 and cond2 <= expect)),
        )

    return test_date


def _test_ratio(info: TorrentDict) -> Tuple[str, bool]:
    logger.debug(f'ratio: {info.get("ratio", 0.0):.2f}')
    return 'ratio >= 1', info.get('ratio', 0.0) >= 1


@click.command()
@common_options_and_arguments
@click.option('-D', '--ignore-date', is_flag=True)
@click.option('-a', '--ignore-ratio', is_flag=True)
@click.option('-y', '--dry-run', is_flag=True)
@click.option('--days', type=int, default=14)
@click.option('--label', default=None)
@click.option('--max-attempts', type=int, default=3)
@click.option('--sleep-time', type=int, default=10)
def main(  # pylint: disable=too-many-arguments
    host: str,
    debug: bool = False,
    netrc: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    ignore_ratio: bool = False,
    ignore_date: bool = False,
    label: Optional[str] = None,
    max_attempts: int = 3,
    dry_run: bool = False,
    max_retries: int = 10,
    days: int = 14,
    backoff_factor: int = 1,
    sleep_time: int = 10,
) -> None:
    """Delete torrents based on certain criteria."""
    if debug:  # pragma: no cover
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.level('INFO')
    client = ruTorrentClient(host,
                             name=username,
                             password=password,
                             max_retries=max_retries,
                             netrc_path=netrc or expanduser('~/.netrc'))
    try:
        torrents = client.list_torrents_dict()
    except HTTPError as e:
        logger.error('Connection failed on list_torrents() call')
        raise click.Abort() from e
    tests = cast(
        TestsDict,
        dict(
            ratio=(ignore_ratio, _test_ratio),
            date=(ignore_date, _test_date_cb(days)),
        ))
    for hash_, info in torrents.items():
        if info['left_bytes'] != 0 or info['custom1'] != label:
            continue
        reason: Optional[str] = None
        can_delete = False
        for key, (can_ignore, test) in tests.items():
            if can_ignore:
                can_delete = True
                reason = f'ignoring {key}'
                break
            reason, can_delete = test(info)
            if can_delete:
                break
        if not can_delete:
            logger.info(f'Cannot delete {info["name"]}')
            continue
        if dry_run:
            logger.info(f'Would delete {info["name"]}, reason: {reason}')
            continue
        logger.info(f'Deleting {info["name"]}, reason: {reason}')
        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            try:
                client.delete(hash_)
            except (xmlrpc.Fault, xmlrpc.ProtocolError) as e:
                logger.exception(e)
                sleep_time = backoff_factor * (2 ** (attempts - 1))
                sleep(sleep_time)
            else:
                sleep(sleep_time)
                break
