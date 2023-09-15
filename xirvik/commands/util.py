"""Utility functions for CLI commands."""
from os.path import expanduser
from types import FrameType
from typing import Any, Callable, Iterator, Sequence, Type
import functools
import itertools
import logging
import pathlib
import re
import sys
import warnings

from click.core import ParameterSource
from loguru import logger
import click
import xdg.BaseDirectory
import yaml

__all__ = ('common_options_and_arguments', 'complete_hosts', 'complete_ports',
           'setup_log_intercept_handler', 'setup_logging')


def setup_logging(debug: bool | None = False) -> None:
    """Shared function to enable logging."""
    if debug:  # pragma: no cover
        setup_log_intercept_handler()
        logger.enable('')
    else:
        logger.configure(handlers=(dict(
            format='<level>{message}</level>',
            level='INFO',
            sink=sys.stderr,
        ),))


def common_options_and_arguments(func: Callable[..., None]) -> Callable[..., None]:
    """
    Shared options and arguments, to be used as a decorator with
    click.command().
    """
    @click.option('-u', '--username', default=None, help='Xirvik user')
    @click.option('-p', '--password', help='Xirvik password')
    @click.option('-r',
                  '--max-retries',
                  type=int,
                  default=10,
                  help='Number of retries for each request (passed to client)')
    @click.option('-d', '--debug', is_flag=True, help='Enable debug level logging')
    @click.option('--backoff-factor',
                  default=5,
                  type=int,
                  help=('Back-off factor used when calculating time to wait to retry '
                        'a failed request'))
    @click.option('--netrc', default=expanduser('~/.netrc'), help='netrc file path')
    @click.option('-C', '--config', help='Configuration file')
    @click.option('-H',
                  '--host',
                  help='Xirvik host (without protocol)',
                  shell_complete=complete_hosts)
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:  # pragma: no cover
        return func(*args, **kwargs)

    return wrapper


def _clean_host(host: str) -> str:
    # Attempt to not break IPv6 addresses
    if '[' not in host and (re.search(r'[0-9]+\:[0-9]+', host) or host == '::1'):
        return host
    # Remove brackets and remove port at end
    return re.sub(r'[\[\]]', '', re.sub(r'\:[0-9]+$', '', host))


def _read_ssh_known_hosts() -> Iterator[str]:
    try:
        with open(expanduser('~/.ssh/known_hosts')) as f:
            for line in f.readlines():
                host_part = line.split()[0]
                if ',' in host_part:
                    yield from (_clean_host(x) for x in host_part.split(','))
                else:
                    yield _clean_host(host_part)
    except FileNotFoundError:
        pass


def _read_netrc_hosts() -> Iterator[str]:
    try:
        with open(expanduser('~/.netrc')) as f:
            yield from (x.split()[1] for x in f.readlines())
    except FileNotFoundError:
        pass


def complete_hosts(_: Any, __: Any, incomplete: str) -> Sequence[str]:
    """
    Returns a list of hosts from SSH known_hosts and ~/.netrc for completion.
    """
    return [
        k for k in itertools.chain(_read_ssh_known_hosts(), _read_netrc_hosts())
        if k.startswith(incomplete)
    ]


def complete_ports(_: Any, __: Any, incomplete: str) -> Sequence[str]:
    """Returns common ports for completion."""
    return [k for k in ('80', '443', '8080') if k.startswith(incomplete)]


class InterceptHandler(logging.Handler):  # pragma: no cover
    """Intercept handler taken from Loguru's documentation."""
    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Find caller from where originated the logged message
        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_log_intercept_handler() -> None:  # pragma: no cover
    """Sets up Loguru to intercept records from the logging module."""
    logging.basicConfig(handlers=(InterceptHandler(),), level=0)


def command_with_config_file(config_file_param_name: str = 'config',
                             default_section: str | None = None) -> Type[click.Command]:
    """
    Returns a custom command class that can read from a configuration file
    in place of missing arguments.

    Parameters
    ----------
    config_file_param_name : str
        The name of the parameter given to Click in ``click.option``.

    default_section : str | None
        Default top key of YAML to read from.
    """
    home = pathlib.Path.home()
    default_config_file_path = pathlib.Path(xdg.BaseDirectory.xdg_config_home) / 'xirvik.yml'
    if sys.platform == 'win32':  # pragma: no cover
        default_config_file_path = home / 'AppData/Roaming/xirvik-tools/config.yml'
    elif sys.platform == 'darwin':  # pragma: no cover
        default_config_file_path = home / 'Library/Application Support/xirvik-tools/config.yml'

    class _ConfigFileCommand(click.Command):
        def invoke(self, ctx: click.Context) -> Any:
            config_file_path = (ctx.params.get(config_file_param_name, default_config_file_path)
                                or default_config_file_path)
            config_data: Any = {}
            debug = ctx.params.get('debug', False)
            try:
                with open(config_file_path) as f:
                    config_data = yaml.safe_load(f)
            except FileNotFoundError:  # pragma no cover
                pass
            if isinstance(config_data, dict):
                alt_data = (config_data.get(default_section, {})
                            if default_section is not None else {})
                for param in ctx.params.keys():
                    if ctx.get_parameter_source(param) == ParameterSource.DEFAULT:
                        yaml_param = param.replace('_', '-')
                        if yaml_param in alt_data:
                            ctx.params[param] = alt_data[yaml_param]
                        elif yaml_param in config_data:
                            ctx.params[param] = config_data[yaml_param]
                ctx.params[config_file_param_name] = config_file_path
            else:  # pragma no cover
                warnings.warn(f'Unexpected type in {config_file_path}: ' + str(type(config_data)))
            try:
                return super().invoke(ctx)
            except Exception as e:
                if debug:  # pragma no cover
                    logger.exception(str(e))
                raise click.Abort() from e

    return _ConfigFileCommand
