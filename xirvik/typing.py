"""Typing helpers."""
from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from datetime import datetime

__all__ = ('FileDownloadStrategy', 'FilePriority', 'HashingState', 'State', 'TorrentInfo',
           'TorrentTrackedFile')


class HashingState(IntEnum):
    """Hashing state of the torrent."""
    NOT_HASHING = 0
    FIRST_HASH_CHECK = 1
    HASHING = 2
    REHASHING = 3


class State(IntEnum):
    """State of the torrent."""
    STOPPED = 0
    STARTED_OR_PAUSED = 1


class TorrentInfo(NamedTuple):
    """Torrent information."""
    hash: str
    is_open: bool
    is_hash_checking: bool
    is_hash_checked: bool
    state: State
    name: str
    size_bytes: int
    completed_chunks: int
    size_chunks: int
    bytes_done: int
    up_total: int
    ratio: float
    up_rate: int
    down_rate: int
    chunk_size: int
    """Chunk size (usually a power of 2)."""
    custom1: str
    """Usually contains the assigned label."""
    peers_accounted: int
    peers_not_connected: int
    peers_connected: int
    peers_complete: int
    left_bytes: int
    priority: int
    state_changed: datetime | None
    skip_total: int
    hashing: HashingState
    chunks_hashed: int
    base_path: str
    """Path before the torrent directory or file."""
    creation_date: datetime | None
    """
    Date torrent was added to the client. Can be ``None`` if this was not captured, or possibly due
    to a crash.
    """
    tracker_focus: int
    is_active: bool
    message: str
    """Message from the server."""
    custom2: str
    free_diskspace: int
    is_private: bool
    is_multi_file: bool
    # unk1: str  # noqa: ERA001
    finished: datetime | None


class FilePriority(IntEnum):
    """
    Single file priority.

    These are based on ruTorrent's code, not rTorrent's.
    """
    DO_NOT_DOWNLOAD = 0
    NORMAL = 1
    HIGH = 2


class FileDownloadStrategy(IntEnum):
    """Single file download strategy."""
    NORMAL = 0
    """Also known as 'trailing chunk first'."""
    LEADING_CHUNK_FIRST = 1


class TorrentTrackedFile(NamedTuple):
    """Contains information about a single file within a torrent."""
    name: str
    """File name without path."""
    number_of_pieces: int
    downloaded_pieces: int
    size_bytes: int
    priority_id: FilePriority
    """Download priority."""
    download_strategy_id: FileDownloadStrategy
    """Download strategy."""
