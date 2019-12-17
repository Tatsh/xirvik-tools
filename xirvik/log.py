"""Logging utility module."""
from logging.handlers import SysLogHandler
import logging
import sys

syslogh = None


def cleanup():
    """Close syslog handle and calls logging.shutdown()."""
    global syslogh

    if syslogh:
        syslogh.close()

    logging.shutdown()


def get_logger(name: str,
               level: int = logging.INFO,
               verbose: bool = False,
               debug: bool = False,
               syslog: bool = False) -> logging.Logger:
    """
    Set up a logger for sys.stderr/stdout and/or syslog.

    Return a logger object.
    """
    global syslogh

    log = logging.getLogger(name)

    if verbose or debug:
        log.setLevel(level if not debug else logging.DEBUG)

        channel = logging.StreamHandler(sys.stdout if debug else sys.stderr)
        channel.setFormatter(
            logging.Formatter('%(levelname)s - %(message)s'))
        channel.setLevel(level if not debug else logging.DEBUG)
        log.addHandler(channel)

    if syslog:
        log.setLevel(level)
        syslogh = SysLogHandler(address='/dev/log')

        syslogh.setFormatter(logging.Formatter('%(message)s'))
        syslogh.setLevel(logging.INFO)
        log.addHandler(syslogh)

    return log
