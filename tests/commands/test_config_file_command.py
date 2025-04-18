"""Tests for xirvik.commands.util.command_with_config_file."""
from __future__ import annotations

from typing import TYPE_CHECKING
import warnings

from click.core import ParameterSource
from xirvik.commands.utils import command_with_config_file

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


def test_no_file(mocker: MockerFixture) -> None:
    ctx = mocker.MagicMock()
    ctx.params.get.return_value = 'test1'
    mocker.patch('xirvik.commands.utils.Path.open', side_effect=FileNotFoundError)
    with warnings.catch_warnings(record=True) as w:
        command_with_config_file()('test1').invoke(ctx)
        assert len(w) == 0


def test_incorrect_type(mocker: MockerFixture) -> None:
    ctx = mocker.MagicMock()
    ctx.params.get.return_value = 'test1'
    mocker.patch('xirvik.commands.utils.Path.open')
    yaml_mock = mocker.patch('xirvik.commands.utils.yaml')
    yaml_mock.safe_load.return_value = None
    with warnings.catch_warnings(record=True) as w:
        command_with_config_file()('test1').invoke(ctx)
        assert len(w) == 1


def test_get_value_from_default_yaml(mocker: MockerFixture) -> None:
    ctx = mocker.MagicMock()
    mocker.patch('xirvik.commands.utils.Path.open')
    yaml_mock = mocker.patch('xirvik.commands.utils.yaml')
    yaml_mock.safe_load.return_value = {'host': '123.com'}
    ctx.params = {'host': None}
    ctx.get_parameter_source.return_value = ParameterSource.DEFAULT
    command_with_config_file()('test1').invoke(ctx)
    assert ctx.params['host'] == '123.com'


def test_get_value_from_alt_yaml(mocker: MockerFixture) -> None:
    ctx = mocker.MagicMock()
    mocker.patch('xirvik.commands.utils.Path.open')
    yaml_mock = mocker.patch('xirvik.commands.utils.yaml')
    yaml_mock.safe_load.return_value = {'host': '123.com', 'cool-command': {'host': '124.com'}}
    ctx.params = {'host': None}
    ctx.get_parameter_source.return_value = ParameterSource.DEFAULT
    command_with_config_file(default_section='cool-command')('test1').invoke(ctx)
    assert ctx.params['host'] == '124.com'


def test_get_value_no_alt(mocker: MockerFixture) -> None:
    ctx = mocker.MagicMock()
    mocker.patch('xirvik.commands.utils.Path.open')
    yaml_mock = mocker.patch('xirvik.commands.utils.yaml')
    yaml_mock.safe_load.return_value = {'host': '121.com', 'cool-command': {}}
    ctx.params = {'host': None}
    ctx.get_parameter_source.return_value = ParameterSource.DEFAULT
    command_with_config_file(default_section='cool-command')('test1').invoke(ctx)
    assert ctx.params['host'] == '121.com'


def test_get_value_no_value(mocker: MockerFixture) -> None:
    ctx = mocker.MagicMock()
    yaml_mock = mocker.patch('xirvik.commands.utils.yaml')
    yaml_mock.safe_load.return_value = {}
    ctx.params = {'host': None}
    ctx.get_parameter_source.return_value = ParameterSource.DEFAULT
    command_with_config_file(default_section='cool-command')('test1').invoke(ctx)
    assert ctx.params['host'] is None


def test_get_value_override_from_cli(mocker: MockerFixture) -> None:
    ctx = mocker.MagicMock()
    yaml_mock = mocker.patch('xirvik.commands.utils.yaml')
    yaml_mock.safe_load.return_value = {'host': '123.com', 'cool-command': {'host': '124.com'}}
    ctx.params = {'host': '125.com'}
    ctx.get_parameter_source.return_value = ParameterSource.COMMANDLINE
    command_with_config_file(default_section='cool-command')('test1').invoke(ctx)
    assert ctx.params['host'] == '125.com'
