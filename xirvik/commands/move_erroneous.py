#!/usr/bin/env python
from functools import partial
from time import sleep
from typing import (Any, Callable, Hashable, Iterator, List, Mapping, Optional,
                    Sequence, Tuple)
import logging
import sys

from ..client import ruTorrentClient
from .util import common_parser, setup_logging_stdout

PREFIX = '/torrents/{}/_completed-not-active'
BAD_MESSAGES = (
    'unregistered torrent',
    "couldn't connect to server",
    'server returned nothing',
)
log: Optional[logging.Logger] = None


def get_name(x: Mapping[str, str]) -> str:
    return x['name']


def get_message(x: Mapping[str, str]) -> str:
    return x['message']


def get_label(x: Mapping[str, str]) -> str:
    return x['custom1']


def get_label_lower(x: Mapping[str, str]) -> str:
    return get_label(x).lower()


def is_hash_checking(x: Mapping[str, bool]) -> bool:
    return x['is_hash_checking']


def complement(x: Callable[..., Any]) -> Callable[..., bool]:
    def z(*args: Any, **kwargs: Any) -> bool:
        return not x(*args, **kwargs)

    return z


def has_one(look_for_list: Sequence[Hashable],
            val: Sequence[Hashable]) -> bool:
    for s in look_for_list:
        if s in val:
            return True
    return False


def has_bad_message(x: Mapping[str, str]) -> bool:
    return has_one(BAD_MESSAGES, x['message'])


def left_bytes_gt_0(x: Mapping[str, int]) -> bool:
    return x['left_bytes'] > 0


# def make_move_to(prefix, label):
#     return '{}/{}'.format(prefix, label)

# make_move_to_prefix = partial(make_move_to, PREFIX)
# mmtp = compose(make_move_to_prefix, get_label_lower)

# def rem0(div, x):
#     return compose(partial(equals, 0), partial_right(mod, div))(x)

# rem_zero_ten = partial(rem0, 10)

# def _should_skip(move_to):
#     return any_pass(is_hash_checking, left_bytes_gt_0,
#                     base_path_check(move_to))

# should_skip = compose(_should_skip, mmtp)

# rem_zero_ten_not_zero = cond((
#     (lambda i: i <= 0, f),
#     (rem_zero_ten, t),
#     (t, t),
# ))


def any_pass(*funcs: Callable[..., bool]) -> Callable[[Any], bool]:
    def ret(x: Any) -> bool:
        for pred in funcs:
            if pred(x):
                return True
        return False

    return ret


# def starts_with(search: str, x: str) -> bool:
#     return str.startswith(x, search)

# def base_path_check(move_to: str) -> bool:
#     return compose(partial(starts_with, move_to), partial(get, 'base_path'))

# def do_if(pred: Callable[..., Any], args: Sequence[Any],
#           func: Callable[..., Any], func_args: Sequence[Any]):
#     if pred(*args):
#         return func(*func_args)


def main() -> int:
    global log
    parser = common_parser()
    parser.add_argument('-a', '--ignore-ratio', action='store_true')
    parser.add_argument('-t', '--sleep-time', default=10, type=int)
    args = parser.parse_args()
    log = setup_logging_stdout(verbose=args.verbose)
    assert log is not None
    client = ruTorrentClient(args.host[0],
                             name=args.username,
                             password=args.password,
                             max_retries=args.max_retries,
                             netrc_path=args.netrc)
    prefix = PREFIX.format(args.username)
    to_delete: List[Tuple[str, str]] = []

    items: Iterator[Tuple[str, Mapping[str, Any]]] = filter(
        lambda x: has_bad_message(x[1]),
        client.list_torrents().items())

    count = 0
    for hash_, info in items:
        log.info('Stopping %s', info['name'])
        client.stop(hash_)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(args.sleep_time)

    should_process_ = compose(complement(bool), partial(get, 'is_active'))
    items = filter(
        lambda: any_pass(is_hash_checking, left_bytes_gt_0,
                         base_path_check(move_to)), filter())

    count = 0
    for hash_, info in items:
        move_to = make_move_to(prefix, info['custom1'].lower())
        name = get_name(info)
        to_delete.append((hash_, name))
        log.info('Moving %s to %s/', name, move_to)
        client.move_torrent(hash_, move_to)
        client.stop(hash_)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(args.sleep_time)

    count = 0
    for hash_, name in to_delete:
        log.info('Removing torrent "%s" (without deleting data)', name)
        client.remove(hash_)
        count += 1
        if count > 0 and (count % 10) == 0:
            sleep(args.sleep_time)

    return 0


if __name__ == '__main__':
    sys.exit(main())
