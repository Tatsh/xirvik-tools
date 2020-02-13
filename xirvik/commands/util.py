from functools import lru_cache
from os.path import basename
from typing import Optional
import argparse
import logging
import sys


@lru_cache()
def setup_logging_stdout(name: Optional[str] = None,
                         verbose: bool = False) -> logging.Logger:
    name = name if name else basename(sys.argv[0])
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    channel = logging.StreamHandler(sys.stdout)
    channel.setFormatter(logging.Formatter('%(message)s'))
    channel.setLevel(logging.DEBUG if verbose else logging.INFO)
    log.addHandler(channel)
    return log


def common_parser() -> argparse.ArgumentParser:
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
