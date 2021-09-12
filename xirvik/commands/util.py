"""Utility functions for CLI commands."""
from functools import lru_cache
from os.path import basename, expanduser
from types import FrameType
from typing import Any, Iterator, Optional, Sequence, Union
import argparse
import itertools
import logging
import re
import sys

from loguru import logger

__all__ = ('common_parser', 'complete_hosts', 'complete_ports',
           'setup_logging_stdout')


@lru_cache()
def setup_logging_stdout(name: Optional[str] = None,
                         verbose: bool = False) -> logging.Logger:
    """Basic way to set up and get a logger.

    Parameters
    ----------
    name : Optional[str]
        Name of the logger.
    verbose : bool
        If log level should be DEBUG instead of INFO.
    """
    name = name if name else basename(sys.argv[0])
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    channel = logging.StreamHandler(sys.stdout)
    channel.setFormatter(logging.Formatter('%(message)s'))
    channel.setLevel(logging.DEBUG if verbose else logging.INFO)
    log.addHandler(channel)
    return log


def common_parser() -> argparse.ArgumentParser:
    """Common parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', required=False, help='Xirvik user')
    parser.add_argument('-p',
                        '--password',
                        required=False,
                        help='Xirvik password')
    parser.add_argument(
        '-r',
        '--max-retries',
        type=int,
        default=10,
        help='Number of retries for each request (passed to client)')
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        help='Enable verbose logging')
    parser.add_argument(
        '--backoff-factor',
        type=int,
        default=5,
        help=('Back-off factor used when calculating time to wait to retry '
              'a failed request'))
    parser.add_argument('--netrc', required=False, help='netrc file path')
    parser.add_argument('host', nargs=1, help='Host name')
    return parser


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


class InterceptHandler(logging.Handler):
    """Intercept handler taken from Loguru's documentation."""
    def emit(self, record: logging.LogRecord) -> None:
        level: Union[str, int]
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Find caller from where originated the logged message
        frame: Optional[FrameType]
        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage())


def setup_log_intercept_handler() -> None:
    """Sets up Loguru to intercept records from the logging module."""
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
