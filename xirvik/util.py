from xirvik.logging import cleanup
import sys


def cleanup_and_exit(status=0):
    cleanup()
    sys.exit(status)


def ctrl_c_handler(signum, frame):
    cleanup()
    raise SystemExit('Signal raised')
