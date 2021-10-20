"""Typing helpers."""
from datetime import datetime
from typing import Callable, NamedTuple, Optional, TypedDict, TypeVar

__all__ = ('Method0', 'Method1', 'TorrentDict')

T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')
Method0 = Callable[[T], V]
Method1 = Callable[[T, U], V]


class TorrentDict(TypedDict):
    """Torrent information."""
    #: Path before the torrent directory or file.
    base_path: str
    #:
    bytes_done: int
    #: Chunk size (usually a power of 2).
    chunk_size: int
    #:
    chunks_hashed: int
    #:
    completed_chunks: int
    #: Date torrent was added to the client. Can be ``None`` if this was not
    #: captured, or possibly due to a crash.
    creation_date: Optional[datetime]
    #: Usually contains the assigned label.
    custom1: str
    #:
    custom2: str
    #:
    down_rate: int
    #:
    free_diskspace: int
    #:
    hashing: bool
    #:
    is_active: int
    #:
    is_hash_checked: bool
    #:
    is_hash_checking: bool
    #:
    is_multi_file: bool
    #: Unknown.
    is_open: bool
    #:
    is_private: bool
    #:
    left_bytes: int
    #: Message from the server.
    message: str
    #:
    name: str
    #:
    peers_accounted: int
    #:
    peers_connected: int
    #:
    peers_not_connected: int
    #:
    priority: int
    #:
    ratio: float
    #:
    size_bytes: int
    #:
    size_chunks: int
    #:
    skip_total: int
    #:
    state: int
    #:
    state_changed: datetime
    #:
    tracker_focus: int
    #:
    up_rate: int
    #:
    up_total: int


class TorrentTrackedFile(NamedTuple):
    """Contains information about a single file within a torrent."""
    #: File name without path.
    name: str
    number_of_pieces: int
    downloaded_pieces: int
    size_bytes: int
    priority_id: int
    download_strategy_id: int
