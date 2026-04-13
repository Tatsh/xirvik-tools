from __future__ import annotations

from typing import TYPE_CHECKING

from xirvik.main import main

if TYPE_CHECKING:
    from click.testing import CliRunner


def test_main(runner: CliRunner) -> None:
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert 'Do something here.' in result.output


def test_main_debug(runner: CliRunner) -> None:
    result = runner.invoke(main, ('--debug',))
    assert result.exit_code == 0


def test_main_help(runner: CliRunner) -> None:
    result = runner.invoke(main, ('-h',))
    assert result.exit_code == 0
    assert 'Entry point.' in result.output
