"""Typing helpers."""
from datetime import datetime
from typing import Callable, Optional, TypeVar

from typing_extensions import TypedDict

__all__ = ('Method0', 'Method1', 'TorrentDict')

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')
Method0 = Callable[[T], V]
Method1 = Callable[[T, U], V]


class TorrentDict(TypedDict):
    base_path: str
    bytes_done: int
    chunk_size: int
    chunks_hashed: int
    completed_chunks: int
    creation_date: Optional[datetime]
    custom1: str
    custom2: str
    down_rate: int
    free_diskspace: int
    hashing: bool
    is_active: int
    is_hash_checked: bool
    is_hash_checking: bool
    is_multi_file: bool
    is_open: bool
    is_private: bool
    left_bytes: int
    message: str
    peers_accounted: int
    peers_connected: int
    peers_not_connected: int
    priority: int
    ratio: float
    size_bytes: int
    size_chunks: int
    skip_total: int
    state: int
    state_changed: datetime
    tracker_focus: int
    up_rate: int
    up_total: int
