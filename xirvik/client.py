"""Client for ruTorrent."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import cached_property
from netrc import netrc
from pathlib import Path
from typing import TYPE_CHECKING, Any, ForwardRef, cast
from urllib.parse import quote
import inspect
import logging
import xmlrpc.client as xmlrpc

from niquests import AsyncSession
from niquests.adapters import AsyncHTTPAdapter
from urllib3.util import Retry
import anyio
import niquests

from .typing import FileDownloadStrategy, FilePriority, TorrentInfo, TorrentTrackedFile
from .utils import parse_header

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterable

__all__ = ('UnexpectedruTorrentError', 'ruTorrentClient')

log = logging.getLogger(__name__)


class UnexpectedruTorrentError(Exception):
    """Raised when an unexpected error occurs."""


class ListTorrentsError(Exception):
    """Raised when ``ruTorrentClient.list_torrents`` has an exception."""


FIRST_YEAR_XIRVIK = 2009


class ruTorrentClient:  # noqa: N801
    """
    ruTorrent client class.

    `Reference on RPC returned fields.`_

    .. _Reference on RPC returned fields.: https://goo.gl/DvmW4c

    Parameters
    ----------
    host : str
        Hostname with no protocol.

    name : str | None
        Username.

        If no name and no password are passed, ``~/.netrc`` will be searched with the host provided.
        The path can be overridden with the ``netrc_path`` argument.

    password : str | None
        Password.

    max_retries : int
        Number of tries to retry any request.

    netrc_path : str | None
        netrc file path.

    backoff_factor : int
        Factor used to calculate back-off time when retrying requests.

    Raises
    ------
    ValueError
        If no netrc entry is found for the host, or if username or password is not provided.
    """
    def __init__(self,
                 host: str,
                 name: str | None = None,
                 password: str | None = None,
                 max_retries: int = 10,
                 netrc_path: str | Path | None = None,
                 backoff_factor: int = 1) -> None:
        if not name and not password:
            if not netrc_path:
                netrc_path = Path('~/.netrc').expanduser()
            netrc_data = netrc(netrc_path).authenticators(host.split(':', maxsplit=1)[0])
            if netrc_data is None:
                msg = f'No netrc entry found for {host}'
                raise ValueError(msg)
            name, _, password = netrc_data
        if name is None:
            msg = 'Username is required'
            raise ValueError(msg)
        if password is None:
            msg = 'Password is required'
            raise ValueError(msg)
        self.name = name
        """Username for authentication."""
        self.password = password
        """Password for authentication."""
        self.host = host
        """Hostname with no protocol."""
        retry = Retry(connect=max_retries,
                      read=max_retries,
                      redirect=False,
                      backoff_factor=backoff_factor)
        self._http_adapter = AsyncHTTPAdapter(max_retries=cast('Any', retry))
        self._session = AsyncSession()
        self._session.mount('http://', self._http_adapter)
        self._session.mount('https://', self._http_adapter)
        self._xmlrpc_proxy = xmlrpc.ServerProxy(f'https://{self.name}:{self.password}@{self.host}'
                                                '/rtorrent/plugins/multirpc/action.php')

    @cached_property
    def http_prefix(self) -> str:
        """HTTP URI for the host."""
        return f'https://{self.host:s}'

    @cached_property
    def multirpc_action_uri(self) -> str:
        """HTTP ``multirpc/action.php`` URI for the host."""
        return f'{self.http_prefix}/rtorrent/plugins/multirpc/action.php'

    @cached_property
    def datadir_action_uri(self) -> str:
        """HTTP ``datadir/action.php`` URI for the host."""
        return f'{self.http_prefix}/rtorrent/plugins/datadir/action.php'

    @cached_property
    def add_torrent_uri(self) -> str:
        """HTTP URI to POST torrents to."""
        return f'{self.http_prefix}/rtorrent/php/addtorrent.php?'

    @cached_property
    def auth(self) -> tuple[str, str]:
        """Basic authentication credentials."""
        return (self.name, self.password)

    async def add_torrent(self, filepath: str, *, start_now: bool = True) -> None:
        """
        Add a torrent. Use ``start_now=False`` to start paused.

        Parameters
        ----------
        filepath : str
            File path to the torrent file.
        start_now : bool
            If the torrent should start immediately.
        """
        filepath_obj = anyio.Path(filepath)
        content = await filepath_obj.read_bytes()
        (await self._session.post(self.add_torrent_uri,
                                  data={'torrents_start_stopped': 'on'} if not start_now else {},
                                  auth=self.auth,
                                  files={'torrent_file': (str(
                                      filepath_obj.name), content)})).raise_for_status()

    async def list_torrents(self) -> AsyncIterator[TorrentInfo]:
        """
        Get all torrent information.

        Yields
        ------
        TorrentInfo
            Information about each torrent.

        Raises
        ------
        ListTorrentsError
            If the response is not as expected.
        """
        r = await self._session.post(self.multirpc_action_uri,
                                     data={
                                         'mode': 'list',
                                         'cmd': 'd.custom=seedingtime'
                                     },
                                     auth=self.auth)
        r.raise_for_status()
        possible_dict = cast('dict[str, list[Any]]', r.json()['t'])
        if not hasattr(possible_dict, 'items'):
            log.debug('Returned: %s', possible_dict)
            msg = f'Unexpected type in response: {type(possible_dict)}'
            raise ListTorrentsError(msg)
        annots = inspect.get_annotations(TorrentInfo)
        for hash_, x in possible_dict.items():
            del x[34]  # Delete unknown field
            type_cls: ForwardRef
            for i, (type_cls, val) in enumerate(
                    zip((t[1] for t in list(annots.items())[1:]), (y.strip() for y in x),
                        strict=False)):
                match type_cls.__forward_arg__:
                    case 'datetime | None':
                        try:
                            x[i] = datetime.fromtimestamp(float(val.strip() or '0'), timezone.utc)
                            # First year xirvik.com existed
                            if x[i].year < FIRST_YEAR_XIRVIK:
                                x[i] = None
                        except ValueError:  # pragma no cover
                            x[i] = None
                    case 'int':
                        x[i] = int(val)
                    case 'float':
                        x[i] = float(val)
                    case 'bool':
                        x[i] = bool(int(val))
                    case 'HashingState' | 'State':
                        x[i] = int(val)
                    case _:
                        x[i] = val
            yield TorrentInfo(hash_, *x)

    async def get_torrent(self, hash_: str) -> tuple[niquests.Response, str]:
        r"""
        Prepare to get a torrent file given a hash.

        Parameters
        ----------
        hash\_ : str
            Hash of the torrent.

        Returns
        -------
        tuple[niquests.Response, str]
            :py:class:`~niquests.Response` object and the file name string.
        """
        source_torrent_uri = (f'{self.http_prefix}/rtorrent/plugins/source/'
                              f'action.php?hash={hash_}')
        r = await self._session.get(source_torrent_uri, auth=self.auth, stream=True)
        r.raise_for_status()
        fn = parse_header(str(r.headers['content-disposition']))[1]['filename']
        return r, fn

    async def move_torrent(self,
                           torrent_hash: str,
                           target_dir: str,
                           *,
                           fast_resume: bool = True) -> None:
        """
        Move a torrent's files to somewhere else on the server.

        Parameters
        ----------
        torrent_hash : str
            Hash of the torrent.
        target_dir : str
            Must be a valid and usable directory.
        fast_resume : bool
            Use fast resumption.

        Raises
        ------
        UnexpectedruTorrentError
            If the server returns errors in the response.
        """
        r = await self._session.post(self.datadir_action_uri,
                                     data={
                                         'hash': torrent_hash,
                                         'datadir': target_dir,
                                         'move_addpath': '1',
                                         'move_datafiles': '1',
                                         'move_fastresume': '1' if fast_resume else '0',
                                     },
                                     auth=self.auth)
        r.raise_for_status()
        json = r.json()
        if json.get('errors'):
            raise UnexpectedruTorrentError(str(json['errors']))

    async def set_label_to_hashes(self, **kwargs: Any) -> None:
        """
        Set a label to a list of info hashes. The label can be a new label.

        To remove a label, pass an empty string as the ``label`` keyword argument.

        Example use::

            client.set_labels(hashes=[hash_1, hash_2],
                              label='my new label')

        Parameters
        ----------
        **kwargs : Any
            Expected keys: ``hashes`` (list of hash strings), ``label`` (str), and optionally
            ``allow_recursive_fix`` (bool), ``recursion_limit`` (int), ``recursion_attempt`` (int).

        Raises
        ------
        TypeError
            If the ``hashes`` or ``label`` keyword arguments are not passed.
        """
        hashes = kwargs.pop('hashes', [])
        label = kwargs.pop('label', None)
        allow_recursive_fix = kwargs.pop('allow_recursive_fix', True)
        recursion_limit = kwargs.pop('recursion_limit', 5)
        recursion_attempt = kwargs.pop('recursion_attempt', 0)
        if not hashes or not label:
            msg = '"hashes" (list) and "label" (str) keyword arguments are required.'
            raise TypeError(msg)
        data = b'mode=setlabel'
        for hash_ in hashes:
            data += f'&hash={hash_}'.encode()
        data += f'&v={label}'.encode() * len(hashes)
        data += b'&s=label' * len(hashes)
        log.debug('set_labels() with data: %s', data.decode())
        r = await self._session.post(self.multirpc_action_uri, data=data, auth=self.auth)
        r.raise_for_status()
        json = r.json()
        if len(json) != len(hashes):
            log.warning(
                'JSON returned should have been an array with same length as hashes list passed '
                'in: %s', json)
            if allow_recursive_fix and recursion_attempt < recursion_limit:
                recursion_attempt += 1
                log.info('Attempting label again '
                         '(%d out of %d)', recursion_attempt, recursion_limit)
                data = b'mode=setlabel'
                new_hashes = []
                async for v in self.list_torrents():
                    hash_ = v.hash
                    if hash_ in hashes or not (v.custom1 or '').strip():
                        data += f'&hash={hash_}'.encode()
                        new_hashes.append(hash_)
                if not new_hashes:
                    log.debug('Found no torrents to correct')
                    return
                await self.set_label_to_hashes(hashes=new_hashes,
                                               label=label,
                                               recursion_limit=recursion_limit,
                                               recursion_attempt=recursion_attempt)
            else:
                log.warning('Passed recursion limit for label fix')

    async def set_label(self, label: str, torrent_hash: str) -> None:
        """
        Set a label to a torrent.

        Parameters
        ----------
        label : str
            Label to use.
        torrent_hash : str
            Hash of the torrent.
        """
        await self.set_label_to_hashes(hashes=[torrent_hash], label=label)

    async def list_files(self, hash_: str) -> AsyncIterator[TorrentTrackedFile]:
        r"""
        List files for a given torrent hash.

        Returns a generator of named tuples with fields (in this order):
        - name
        - total number of pieces
        - number of pieces downloaded
        - size in bytes
        - priority
        - download strategy

        Example use:

        .. code-block:: python

           async for name, pieces, pieces_dl, size, priority, dl_strategy in client.list_files():

        Parameters
        ----------
        hash\_ : str
            Hash of the torrent.

        Yields
        ------
        TorrentTrackedFile
            Named tuple with file information.
        """
        r = await self._session.post(
            self.multirpc_action_uri,
            data=(f'mode=fls&hash={hash_}' + '&' + '&'.join(f'cmd={x}' for x in (
                quote('f.prioritize_first='),
                quote('f.prioritize_last='),
            ))),
            auth=self.auth)
        r.raise_for_status()
        for x in r.json():
            x[1] = int(x[1])
            x[2] = int(x[2])
            x[3] = int(x[3])
            x[4] = FilePriority(int(x[4]))
            x[5] = FileDownloadStrategy(int(x[5]))
            yield TorrentTrackedFile(*x[:6])

    async def list_all_files(self) -> AsyncIterator[TorrentTrackedFile]:
        """
        List all files tracked by rTorrent.

        If there are thousands of torrents, this may take well over 10 minutes.

        Returns a generator of tracked files.

        Yields
        ------
        TorrentTrackedFile
            Named tuple with file information.
        """
        async for info in self.list_torrents():
            async for tracked_file in self.list_files(info.hash):
                yield tracked_file

    async def delete(self, hash_: str) -> None:
        r"""
        Delete a torrent and its files by hash.

        Use the remove() method to remove the torrent but keep the data.

        Returns if successful. Faults are converted to :py:class:`xmlrpc.Fault` exceptions.

        Parameters
        ----------
        hash\_ : str
            Hash of the torrent.
        """
        await anyio.to_thread.run_sync(self._delete_sync, hash_)

    def _delete_sync(self, hash_: str) -> None:
        mc = xmlrpc.MultiCall(self._xmlrpc_proxy)
        getattr(mc, 'd.custom5.set')(hash_, '1')
        getattr(mc, 'd.delete_tied')(hash_)
        getattr(mc, 'd.erase')(hash_)
        for x in mc().results:
            x_typed = cast('dict[str, Any]', x)
            if 'faultCode' in x_typed and 'faultString' in x_typed:
                raise xmlrpc.Fault(x_typed['faultCode'], x_typed['faultString'])

    async def remove(self, hash_: str) -> None:
        r"""
        Remove a torrent from the client but keep the data.

        Use the delete() method to remove and delete the torrent data.

        Returns if successful. Can raise a :py:class:`~niquests.exceptions.HTTPError` exception.

        Parameters
        ----------
        hash\_ : str
            Hash of the torrent.
        """
        (await self._session.post(self.multirpc_action_uri,
                                  data={
                                      'mode': 'remove',
                                      'hash': hash_
                                  },
                                  auth=self.auth)).raise_for_status()

    async def stop(self, hash_: str) -> None:
        r"""
        Stop a torrent by hash.

        Returns if successful. Can raise a :py:class:`~niquests.exceptions.HTTPError` exception.

        Parameters
        ----------
        hash\_ : str
            Hash of the torrent.
        """
        (await self._session.post(self.multirpc_action_uri,
                                  data={
                                      'mode': 'stop',
                                      'hash': hash_
                                  },
                                  auth=self.auth)).raise_for_status()

    async def add_torrent_url(self, url: str) -> None:
        """
        Add a torrent via URI.

        Parameters
        ----------
        url : str
            URI to the torrent file. Must be available either under the current credentials or
            public.
        """
        (await self._session.post(self.add_torrent_uri, data={'url': url},
                                  auth=self.auth)).raise_for_status()

    async def edit_torrents(self,
                            hashes: Iterable[str],
                            *,
                            comment: str | None = None,
                            private: bool | None = None,
                            trackers: Iterable[str] | None = None) -> niquests.Response:
        """
        Edit torrent properties.

        Parameters
        ----------
        hashes : Iterable[str]
            List of torrent hashes to edit.
        comment : str | None
            Comment to set.
        private : bool | None
            Value for the private flag.
        trackers : Iterable[str] | None
            Tracker URLs.

        Returns
        -------
        niquests.Response
            The response object.
        """
        r = await self._session.post(f'{self.http_prefix}/rtorrent/plugins/edit/action.php',
                                     data=[
                                         *(({
                                             'comment': comment.strip(),
                                             'set_comment': '1'
                                         } if comment else {}) | ({
                                             'private': '1' if private else '0',
                                             'set_private': '1',
                                         } if private is not None else {}) | ({
                                             'set_trackers': '1'
                                         } if trackers else {})).items(),
                                         *(('hash', h) for h in hashes or []),
                                         *(('tracker', t) for t in trackers or [])
                                     ],
                                     auth=self.auth)
        r.raise_for_status()
        return r
