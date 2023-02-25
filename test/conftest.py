"""Configuration for Pytest."""
from typing import NoReturn
import os
import pathlib

from click.testing import CliRunner
import pytest

# pylint: disable=missing-function-docstring,protected-access
# pylint: disable=redefined-outer-name,unused-argument,unused-variable

if os.getenv('_PYTEST_RAISE', '0') != '0':  # pragma no cover

    @pytest.hookimpl(tryfirst=True)  # type: ignore[misc]
    def pytest_exception_interact(call: pytest.CallInfo[None]) -> NoReturn:
        assert call.excinfo is not None
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)  # type: ignore[misc]
    def pytest_internalerror(excinfo: pytest.ExceptionInfo[Exception]) -> NoReturn:
        raise excinfo.value


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def tmp_netrc(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    netrc = tmp_path / '.netrc'
    netrc.write_text('machine machine.com login some_name password pass\n')
    monkeypatch.setenv('HOME', str(tmp_path))
    return netrc
