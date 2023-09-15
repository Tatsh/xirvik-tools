#!/usr/bin/env python
"""
Deletes old torrents based on specified criteria.
"""
from datetime import datetime, timedelta
from os.path import expanduser
from time import sleep
from typing import Callable
import xmlrpc.client as xmlrpc

from loguru import logger
from requests.exceptions import HTTPError
import click

from xirvik.typing import TorrentInfo

from ..client import ruTorrentClient
from .util import command_with_config_file, common_options_and_arguments, setup_logging

TestCallable = Callable[[TorrentInfo], tuple[str, bool]]
TestsDict = dict[str, tuple[bool, TestCallable]]


def _test_date_cb(days: int = 14) -> TestCallable:
    def test_date(info: TorrentInfo) -> tuple[str, bool]:
        condition1 = info.creation_date
        condition2 = info.state_changed
        expect = datetime.now() - timedelta(days=days)
        logger.debug(f'creation date: {condition1}')
        logger.debug(f'state changed: {condition2}')
        logger.debug(f'{condition1} <= {expect} or')
        logger.debug(f'    {condition2} <= {expect}')
        return (
            f'over {days} days seeded',
            bool((condition1 and condition1 <= expect) or (condition2 and condition2 <= expect)),
        )

    return test_date


def _test_ratio(info: TorrentInfo) -> tuple[str, bool]:
    logger.debug(f'ratio: {info.ratio:.2f}')
    return 'ratio >= 1', info.ratio >= 1


@click.command(cls=command_with_config_file('config', 'delete-old'))
@common_options_and_arguments
@click.option('-D', '--ignore-date', is_flag=True)
@click.option('-a', '--ignore-ratio', is_flag=True)
@click.option('-y', '--dry-run', is_flag=True)
@click.option('--days', type=int, default=14)
@click.option('--label', default=None)
@click.option('--max-attempts', type=int, default=3)
@click.option('--sleep-time', type=int, default=10)
def main(host: str,
         debug: bool = False,
         netrc: str | None = None,
         username: str | None = None,
         password: str | None = None,
         ignore_ratio: bool = False,
         ignore_date: bool = False,
         label: str | None = None,
         max_attempts: int = 3,
         dry_run: bool = False,
         max_retries: int = 10,
         days: int = 14,
         backoff_factor: int = 1,
         sleep_time: int = 10,
         config: str | None = None) -> None:
    """Delete torrents based on certain criteria."""
    setup_logging(debug)
    client = ruTorrentClient(host,
                             name=username,
                             password=password,
                             max_retries=max_retries,
                             netrc_path=netrc or expanduser('~/.netrc'))
    try:
        torrents = client.list_torrents()
    except HTTPError as e:
        logger.error('Connection failed on list_torrents() call')
        raise click.Abort() from e
    tests = dict(
        ratio=(ignore_ratio, _test_ratio),
        date=(ignore_date, _test_date_cb(days)),
    )
    for info in torrents:
        if info.left_bytes != 0 or info.custom1 != label:
            continue
        reason: str | None = None
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
            logger.info(f'Cannot delete {info.name}')
            continue
        if dry_run:
            logger.info(f'Would delete {info.name}, reason: {reason}')
            continue
        logger.info(f'Deleting {info.name}, reason: {reason}')
        attempts = 0
        while attempts < max_attempts:
            attempts += 1
            try:
                client.delete(info.hash)
            except (xmlrpc.Fault, xmlrpc.ProtocolError):
                sleep_time = backoff_factor * (2 ** (attempts - 1))
                sleep(sleep_time)
            else:
                sleep(sleep_time)
                break
