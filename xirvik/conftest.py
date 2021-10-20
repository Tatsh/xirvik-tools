"""Configuration for Pytest."""
from typing import Any, NoReturn
import os
import pathlib

from click.testing import CliRunner
import pytest

# pylint: disable=missing-function-docstring,protected-access,no-self-use
# pylint: disable=redefined-outer-name,unused-argument

if os.getenv('_PYTEST_RAISE', '0') != '0':  # pragma no cover

    @pytest.hookimpl(tryfirst=True)  # type: ignore[misc]
    def pytest_exception_interact(call: Any) -> NoReturn:
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)  # type: ignore[misc]
    def pytest_internalerror(excinfo: Any) -> NoReturn:
        raise excinfo.value


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def tmp_netrc(tmp_path: pathlib.Path,
              monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login somename password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    return netrc
