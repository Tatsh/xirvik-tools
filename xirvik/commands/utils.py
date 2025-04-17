"""Utility functions for CLI commands."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
import functools
import itertools
import logging
import re
import warnings

from click.core import ParameterSource
from typing_extensions import override
import click
import platformdirs
import yaml

if TYPE_CHECKING:  # pragma no cover
    from collections.abc import Callable, Iterator

__all__ = ('common_options_and_arguments', 'complete_hosts', 'complete_ports')

logger = logging.getLogger(__name__)


def common_options_and_arguments(func: Callable[..., None]) -> Callable[..., None]:
    """Shared options and arguments, to be used as a decorator with ``click.command()``."""
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
    @click.option('--netrc', default=Path('~/.netrc').expanduser, help='netrc file path')
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
        with Path('~/.ssh/known_hosts').expanduser().open(encoding='utf-8') as f:
            for line in f:
                host_part = line.split()[0]
                if ',' in host_part:
                    yield from (_clean_host(x) for x in host_part.split(','))
                else:
                    yield _clean_host(host_part)
    except FileNotFoundError:
        pass


def _read_netrc_hosts() -> Iterator[str]:
    try:
        with Path('~/.netrc').expanduser().open(encoding='utf-8') as f:
            yield from (x.split()[1] for x in f)
    except FileNotFoundError:
        pass


def complete_hosts(_: Any, __: Any, incomplete: str) -> list[str]:
    """Return a list of hosts from SSH known_hosts and ``~/.netrc`` for completion."""
    return [
        k for k in itertools.chain(_read_ssh_known_hosts(), _read_netrc_hosts())
        if k.startswith(incomplete)
    ]


def complete_ports(_: Any, __: Any, incomplete: str) -> list[str]:
    """Return common ports for completion."""
    return [k for k in ('80', '443', '8080') if k.startswith(incomplete)]


def command_with_config_file(config_file_param_name: str = 'config',
                             default_section: str | None = None) -> type[click.Command]:
    """
    Return a command class that can read from a configuration file in place of missing arguments.

    Parameters
    ----------
    config_file_param_name : str
        The name of the parameter given to Click in ``click.option``.

    default_section : str | None
        Default top key of YAML to read from.
    """
    default_config_file_path = f'{platformdirs.user_config_dir()}/xirvik.yml'

    class _ConfigFileCommand(click.Command):
        @override
        def invoke(self, ctx: click.Context) -> Any:
            config_file_path: str | Path = (ctx.params.get(
                config_file_param_name, default_config_file_path) or default_config_file_path)
            config_file_path = Path(config_file_path).expanduser()
            config_data: Any = {}
            debug = ctx.params.get('debug', False)
            try:
                with config_file_path.open(encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            except FileNotFoundError:  # pragma no cover
                pass
            if isinstance(config_data, dict):
                alt_data = (config_data.get(default_section, {})
                            if default_section is not None else {})
                for param in ctx.params:
                    if ctx.get_parameter_source(param) == ParameterSource.DEFAULT:
                        yaml_param = param.replace('_', '-')
                        if yaml_param in alt_data:
                            ctx.params[param] = alt_data[yaml_param]
                        elif yaml_param in config_data:
                            ctx.params[param] = config_data[yaml_param]
                ctx.params[config_file_param_name] = config_file_path
            else:  # pragma no cover
                warnings.warn(f'Unexpected type in {config_file_path}: {type(config_data)}',
                              stacklevel=1)
            try:
                return super().invoke(ctx)
            except Exception as e:
                if debug:  # pragma no cover
                    logger.exception('Error caught.')
                raise click.Abort from e

    return _ConfigFileCommand
