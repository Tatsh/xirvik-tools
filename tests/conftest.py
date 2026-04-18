"""Configuration for Pytest."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, NoReturn
import os

from click.testing import CliRunner
import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterable
    import pathlib

if os.getenv('_PYTEST_RAISE', '0') != '0':  # pragma no cover

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call: pytest.CallInfo[None]) -> NoReturn:
        assert call.excinfo is not None
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo: pytest.ExceptionInfo[BaseException]) -> NoReturn:
        raise excinfo.value


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def tmp_netrc(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    return netrc


async def alist(ait: AsyncIterator[Any]) -> list[Any]:
    """Collect an async iterator into a list."""
    return [item async for item in ait]


async def async_iter(items: Iterable[Any]) -> AsyncIterator[Any]:  # noqa: RUF029
    """
    Create an async iterator from a sync iterable.

    Parameters
    ----------
    items : Iterable[Any]
        Items to iterate over.

    Yields
    ------
    Any
        Each item from the iterable.
    """
    for item in items:
        yield item
