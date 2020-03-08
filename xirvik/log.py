"""Logging utility module."""
from functools import lru_cache
from os.path import isfile
from logging.handlers import SysLogHandler
import logging
import sys
import syslog

from typing_extensions import Final

__all__ = ('get_logger', )

MAC_SYSLOG_PATH: Final = '/var/run/syslog'


@lru_cache()
def get_logger(name: str,
               level: int = logging.INFO,
               verbose: bool = False,
               debug: bool = False,
               use_syslog: bool = False) -> logging.Logger:
    """
    Set up a logger for sys.stderr/stdout and/or syslog.

    Return a logger object.
    """
    log = logging.getLogger(name)
    if verbose or debug:
        log.setLevel(level if not debug else logging.DEBUG)
        channel = logging.StreamHandler(sys.stdout if debug else sys.stderr)
        channel.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        channel.setLevel(level if not debug else logging.DEBUG)
        log.addHandler(channel)
    if use_syslog:
        log.setLevel(level)
        is_mac = isfile(MAC_SYSLOG_PATH)
        handler = SysLogHandler(
            address='/dev/log' if not is_mac else MAC_SYSLOG_PATH,
            facility=syslog.LOG_USER if not is_mac else syslog.LOG_LOCAL1)
        handler.setFormatter(logging.Formatter('%(message)s'))
        handler.setLevel(logging.INFO)
        log.addHandler(handler)
    return log
