"""Deletes old torrents based on specified criteria."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep
import logging
import xmlrpc.client as xmlrpc

from bascom import setup_logging
from requests.exceptions import HTTPError
from xirvik.client import ruTorrentClient
from xirvik.typing import TorrentInfo
import click

from .utils import command_with_config_file, common_options_and_arguments

log = logging.getLogger(__name__)
TestCallable = Callable[[TorrentInfo], tuple[str, bool]]
TestsDict = dict[str, tuple[bool, TestCallable]]


def _test_date_cb(days: int = 14) -> TestCallable:
    def test_date(info: TorrentInfo) -> tuple[str, bool]:
        condition1 = info.state_changed
        expect = datetime.now(timezone.utc) - timedelta(days=days)
        log.debug('State changed: %s', condition1)
        log.debug('%s <= %s', condition1, expect)
        return (
            f'over {days} days seeded',
            bool(condition1 and condition1 <= expect),
        )

    return test_date


def _test_ratio(info: TorrentInfo) -> tuple[str, bool]:
    log.debug('ratio: %.2f', info.ratio)
    return 'ratio >= 1', info.ratio >= 1


@click.command(cls=command_with_config_file('config', 'delete-old'))
@common_options_and_arguments
@click.option('--days', type=int, default=14)
@click.option('--label', default=None)
@click.option('--max-attempts', type=int, default=3)
@click.option('--sleep-time', type=int, default=10)
@click.option('-D', '--ignore-date', is_flag=True)
@click.option('-a', '--ignore-ratio', is_flag=True)
@click.option('-y', '--dry-run', is_flag=True)
def main(
        host: str,
        netrc: str | None = None,
        username: str | None = None,
        password: str | None = None,
        label: str | None = None,
        max_attempts: int = 3,
        max_retries: int = 10,
        days: int = 14,
        backoff_factor: int = 1,
        sleep_time: int = 10,
        config: str | None = None,  # noqa: ARG001
        *,
        debug: bool = False,
        ignore_ratio: bool = False,
        ignore_date: bool = False,
        dry_run: bool = False) -> None:
    """Delete torrents based on certain criteria."""  # noqa: DOC501
    setup_logging(debug=debug, loggers={'urllib3': {}, 'xirvik': {}})
    client = ruTorrentClient(host,
                             name=username,
                             password=password,
                             max_retries=max_retries,
                             netrc_path=netrc or Path('~/.netrc').expanduser())
    try:
        torrents = client.list_torrents()
    except HTTPError as e:
        log.exception('Connection failed on list_torrents() call')
        raise click.Abort from e
    tests = {
        'ratio': (ignore_ratio, _test_ratio),
        'date': (ignore_date, _test_date_cb(days)),
    }
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
            log.info('Cannot delete %s', info.name)
            continue
        if dry_run:
            log.info('Would delete %s, reason: %s', info.name, reason)
            continue
        log.info('Deleting %s, reason: %s', info.name, reason)
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
