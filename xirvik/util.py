"""General utility module."""
from hashlib import sha1
from hmac import compare_digest
from os import R_OK, access, environ, stat
from os.path import isdir, join as path_join, realpath
from typing import (Any, BinaryIO, Iterable, Iterator, NoReturn, Optional,
                    Sequence, TypeVar, Union, cast)
import argparse
import platform
import struct
import sys

import benc

__all__ = (
    'cleanup_and_exit',
    'ctrl_c_handler',
    'VerificationError',
    'verify_torrent_contents',
    'ReadableDirectoryListAction',
)

T = TypeVar('T')

# pylint: disable=too-few-public-methods


class ReadableDirectoryAction(argparse.Action):
    """Checks if a directory argument is a directory and is readable."""
    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 values: Optional[Union[str, Sequence[Any]]],
                 option_string: Optional[str] = None) -> None:
        prospective_dir = values
        if not isdir(cast(str, prospective_dir)):
            raise argparse.ArgumentTypeError(
                '%s is not a valid directory' % (prospective_dir,))
        # Since macOS 10.15, the Python binary will need access to this
        # directory and a prompt from TCC must appear for this to work
        # Because of TCC becoming more strict, hecking with access() is not
        # reliable on macOS
        if platform.system() == 'Darwin':
            return
        if access(cast(str, prospective_dir), R_OK):
            setattr(namespace, self.dest, realpath(cast(str, prospective_dir)))
            return
        username = environ['USER']
        raise argparse.ArgumentTypeError(
            f'{prospective_dir} is not a readable directory (checking as user '
            f'{username})')


class ReadableDirectoryListAction(argparse.Action):
    """
    Checks if a list of directories argument is a directory and all are
    readable..
    """
    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 values: Optional[Union[str, Sequence[Any]]],
                 option_string: Optional[str] = None) -> None:
        dirs = []
        kwa = dict(self._get_kwargs())
        parent = ReadableDirectoryAction(**kwa)

        for prospective_dir in cast(Sequence[Any], values):
            ns = argparse.Namespace()
            ns.directory = prospective_dir
            parent(parser, ns, prospective_dir, option_string)
            dirs.append(ns.directory)

        setattr(namespace, self.dest, dirs)


# pylint: enable=too-few-public-methods


def ctrl_c_handler(signum: int, frame: Any) -> NoReturn:
    """Used as a TERM signal handler. Arguments are ignored."""
    raise SystemExit('Signal raised')  # pragma: no cover
