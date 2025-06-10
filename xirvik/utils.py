"""Utility functions."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ('parse_header',)


def _parseparam(param: str) -> Iterator[str]:
    while param[:1] == ';':
        param = param[1:]
        end = param.find(';')
        while end > 0 and (param.count('"', 0, end) - param.count('\\"', 0, end)) % 2:
            end = param.find(';', end + 1)
        if end < 0:
            end = len(param)
        f = param[:end]
        yield f.strip()
        param = param[end:]


def parse_header(line: str) -> tuple[str, dict[str, str]]:
    """
    Parse a Content-type like header.

    Return the main content-type and a dictionary of options.
    """
    parts = _parseparam(';' + line)
    key = next(parts)
    pdict = {}
    for p in parts:
        if (i := p.find('=')) >= 0:
            name = p[:i].strip().lower()
            value = p[i + 1:].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':  # noqa: PLR2004
                value = value[1:-1].replace('\\\\', '\\').replace('\\"', '"')
            pdict[name] = value
    return key, pdict
