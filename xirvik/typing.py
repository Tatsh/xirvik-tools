"""Typing helpers."""
from datetime import datetime
from typing import Callable, NamedTuple, Optional, TypeVar

__all__ = ('Method0', 'Method1', 'TorrentInfo', 'TorrentTrackedFile')

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')
Method0 = Callable[[T], V]
Method1 = Callable[[T, U], V]


class TorrentInfo(NamedTuple):
    """Torrent information."""
    hash: str
    is_open: bool
    is_hash_checking: bool
    is_hash_checked: bool
    state: int
    name: str
    size_bytes: int
    completed_chunks: int
    size_chunks: int
    bytes_done: int
    up_total: int
    ratio: float
    up_rate: int
    down_rate: int
    #: Chunk size (usually a power of 2).
    chunk_size: int
    #: Usually contains the assigned label.
    custom1: str
    peers_accounted: int
    peers_not_connected: int
    peers_connected: int
    peers_complete: int
    left_bytes: int
    priority: int
    state_changed: Optional[datetime]
    skip_total: int
    hashing: bool
    chunks_hashed: int
    #: Path before the torrent directory or file.
    base_path: str
    #: Date torrent was added to the client. Can be ``None`` if this was not
    #: captured, or possibly due to a crash.
    creation_date: Optional[datetime]
    tracker_focus: int
    is_active: bool
    #: Message from the server.
    message: str
    custom2: str
    free_diskspace: int
    is_private: bool
    is_multi_file: bool


class TorrentTrackedFile(NamedTuple):
    """Contains information about a single file within a torrent."""
    #: File name without path.
    name: str
    number_of_pieces: int
    downloaded_pieces: int
    size_bytes: int
    priority_id: int
    download_strategy_id: int
