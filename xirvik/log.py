"""Logging utility module."""
from functools import lru_cache
from logging.handlers import SysLogHandler
import logging
import sys


@lru_cache()
def get_logger(name: str,
               level: int = logging.INFO,
               verbose: bool = False,
               debug: bool = False,
               syslog: bool = False) -> logging.Logger:
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
    if syslog:
        log.setLevel(level)
        syslogh = SysLogHandler(address='/dev/log')
        syslogh.setFormatter(logging.Formatter('%(message)s'))
        syslogh.setLevel(logging.INFO)
        log.addHandler(syslogh)
    return log
