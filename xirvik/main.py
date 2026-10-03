"""Main script."""
from __future__ import annotations

from bascom import setup_logging
import click

__all__ = ('main',)


@click.command(context_settings={'help_option_names': ('-h', '--help')})
@click.option('-d', '--debug', help='Enable debug level logging.', is_flag=True)
def main(*, debug: bool = False) -> None:
    """Entry point."""
    setup_logging(debug=debug, loggers={})
    click.echo('Do something here.')
