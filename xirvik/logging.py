from logging.handlers import SysLogHandler
import logging
import sys

syslogh = None


def cleanup():
    global syslogh

    if syslogh:
        syslogh.close()

    logging.shutdown()


def get_logger(name,
               level=logging.INFO,
               verbose=False,
               debug=False,
               syslog=False):
    global syslogh

    log = logging.getLogger(name)

    if verbose or debug:
        log.setLevel(level if not debug else logging.DEBUG)

        channel = logging.StreamHandler(sys.stdout if debug else sys.stderr)
        channel.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        channel.setLevel(level if not debug else logging.DEBUG)
        log.addHandler(channel)

    if syslog:
        syslogh = SysLogHandler(address='/dev/log')

        syslogh.setFormatter(logging.Formatter('%(message)s'))
        syslogh.setLevel(logging.INFO)
        log.addHandler(syslogh)

    return log
