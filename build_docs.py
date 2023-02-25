#!/usr/bin/env python
import subprocess as sp

import click


@click.command('build_docs')
@click.option('-b',
              default='html',
              required=True,
              help='Builder to use (default: html)')
def build_docs(b: str) -> None:
    try:
        sp.run(('sphinx-build', '-b', b, 'docs', 'build'), check=True)
    except sp.CalledProcessError as e:
        raise click.Abort() from e


if __name__ == '__main__':
    build_docs()  # pylint: disable=no-value-for-parameter
