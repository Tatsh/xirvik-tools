"""Tests for xirvik.commands.util.command_with_config_file."""
import warnings

from click.core import ParameterSource
from pytest_mock.plugin import MockerFixture

from ..util import command_with_config_file

# pylint: disable=missing-function-docstring,protected-access,no-self-use,redefined-outer-name,unused-argument


def test_no_file(mocker: MockerFixture):
    ctx = mocker.MagicMock()
    open_mock = mocker.patch('builtins.open')
    open_mock.side_effect = FileNotFoundError()
    with warnings.catch_warnings(record=True) as w:
        command_with_config_file()('test1').invoke(ctx)
        assert len(w) == 0


def test_incorrect_type(mocker: MockerFixture):
    ctx = mocker.MagicMock()
    yaml_mock = mocker.patch('xirvik.commands.util.yaml')
    yaml_mock.safe_load.return_value = None
    with warnings.catch_warnings(record=True) as w:
        command_with_config_file()('test1').invoke(ctx)
        assert len(w) == 1


def test_get_value_from_default_yaml(mocker: MockerFixture):
    ctx = mocker.MagicMock()
    yaml_mock = mocker.patch('xirvik.commands.util.yaml')
    yaml_mock.safe_load.return_value = {'host': '123.com'}
    ctx.params = {'host': None}
    ctx.get_parameter_source.return_value = ParameterSource.DEFAULT
    command_with_config_file()('test1').invoke(ctx)
    assert ctx.params['host'] == '123.com'


def test_get_value_from_alt_yaml(mocker: MockerFixture):
    ctx = mocker.MagicMock()
    yaml_mock = mocker.patch('xirvik.commands.util.yaml')
    yaml_mock.safe_load.return_value = {
        'host': '123.com',
        'cool-command': {
            'host': '124.com'
        }
    }
    ctx.params = {'host': None}
    ctx.get_parameter_source.return_value = ParameterSource.DEFAULT
    command_with_config_file(
        default_section='cool-command')('test1').invoke(ctx)
    assert ctx.params['host'] == '124.com'


def test_get_value_no_alt(mocker: MockerFixture):
    ctx = mocker.MagicMock()
    yaml_mock = mocker.patch('xirvik.commands.util.yaml')
    yaml_mock.safe_load.return_value = {'host': '121.com', 'cool-command': {}}
    ctx.params = {'host': None}
    ctx.get_parameter_source.return_value = ParameterSource.DEFAULT
    command_with_config_file(
        default_section='cool-command')('test1').invoke(ctx)
    assert ctx.params['host'] == '121.com'


def test_get_value_no_value(mocker: MockerFixture):
    ctx = mocker.MagicMock()
    yaml_mock = mocker.patch('xirvik.commands.util.yaml')
    yaml_mock.safe_load.return_value = {}
    ctx.params = {'host': None}
    ctx.get_parameter_source.return_value = ParameterSource.DEFAULT
    command_with_config_file(
        default_section='cool-command')('test1').invoke(ctx)
    assert ctx.params['host'] is None


def test_get_value_override_from_cli(mocker: MockerFixture):
    ctx = mocker.MagicMock()
    yaml_mock = mocker.patch('xirvik.commands.util.yaml')
    yaml_mock.safe_load.return_value = {
        'host': '123.com',
        'cool-command': {
            'host': '124.com'
        }
    }
    ctx.params = {'host': '125.com'}
    ctx.get_parameter_source.return_value = ParameterSource.COMMANDLINE
    command_with_config_file(
        default_section='cool-command')('test1').invoke(ctx)
    assert ctx.params['host'] == '125.com'
