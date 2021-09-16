"""Utility functions for CLI commands."""
from os.path import expanduser
from types import FrameType
from typing import Any, Callable, Iterator, Optional, Sequence, Union
import functools
import itertools
import logging
import re

from loguru import logger
import click

__all__ = ('common_options_and_arguments', 'complete_hosts', 'complete_ports',
           'setup_log_intercept_handler')


def common_options_and_arguments(
        func: Callable[..., None]) -> Callable[..., None]:
    """
    Shared options and arguments, to be used as a decorator with
    click.command().
    """
    @click.option('-u', '--username', default=None, help='Xirvik user')
    @click.option('-p', '--password', help='Xirvik password')
    @click.option('-r',
                  '--max-retries',
                  type=int,
                  default=10,
                  help='Number of retries for each request (passed to client)')
    @click.option('-d',
                  '--debug',
                  is_flag=True,
                  help='Enable debug level logging')
    @click.option(
        '--backoff-factor',
        default=5,
        type=int,
        help=('Back-off factor used when calculating time to wait to retry '
              'a failed request'))
    @click.option('--netrc',
                  default=expanduser('~/.netrc'),
                  help='netrc file path')
    @click.argument('host', shell_complete=complete_hosts)
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:  # pragma: no cover
        return func(*args, **kwargs)

    return wrapper


def _clean_host(s: str) -> str:
    # Attempt to not break IPv6 addresses
    if '[' not in s and (re.search(r'[0-9]+\:[0-9]+', s) or s == '::1'):
        return s
    # Remove brackets and remove port at end
    return re.sub(r'[\[\]]', '', re.sub(r'\:[0-9]+$', '', s))


def _read_ssh_known_hosts() -> Iterator[str]:
    try:
        with open(expanduser('~/.ssh/known_hosts')) as f:
            for line in f.readlines():
                host_part = line.split()[0]
                if ',' in host_part:
                    yield from (_clean_host(x) for x in host_part.split(','))
                else:
                    yield _clean_host(host_part)
    except FileNotFoundError:
        pass


def _read_netrc_hosts() -> Iterator[str]:
    try:
        with open(expanduser('~/.netrc')) as f:
            yield from (x.split()[1] for x in f.readlines())
    except FileNotFoundError:
        pass


def complete_hosts(_: Any, __: Any, incomplete: str) -> Sequence[str]:
    """
    Returns a list of hosts from SSH known_hosts and ~/.netrc for completion.
    """
    return [
        k
        for k in itertools.chain(_read_ssh_known_hosts(), _read_netrc_hosts())
        if k.startswith(incomplete)
    ]


def complete_ports(_: Any, __: Any, incomplete: str) -> Sequence[str]:
    """Returns common ports for completion."""
    return [k for k in ('80', '443', '8080') if k.startswith(incomplete)]


class InterceptHandler(logging.Handler):  # pragma: no cover
    """Intercept handler taken from Loguru's documentation."""
    def emit(self, record: logging.LogRecord) -> None:
        level: Union[str, int]
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Find caller from where originated the logged message
        frame: Optional[FrameType] = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage())


def setup_log_intercept_handler() -> None:  # pragma: no cover
    """Sets up Loguru to intercept records from the logging module."""
    logging.basicConfig(handlers=(InterceptHandler(),), level=0)
