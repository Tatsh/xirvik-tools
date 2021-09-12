"""General utility module."""
from typing import Any, NoReturn

__all__ = ('ctrl_c_handler',)


def ctrl_c_handler(_: int, __: Any) -> NoReturn:  # pragma: no cover
    """Used as a TERM signal handler. Arguments are ignored."""
    raise SystemExit('Signal raised')
