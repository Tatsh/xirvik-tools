"""Client for ruTorrent."""
from datetime import datetime
from enum import IntEnum
from netrc import netrc
from os.path import expanduser
from typing import Any, Final, Iterator, cast
from urllib.parse import quote
import logging
import xmlrpc.client as xmlrpc

from cached_property import cached_property
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import requests

from .typing import FileDownloadStrategy, FilePriority, TorrentInfo, TorrentTrackedFile
from .utils import parse_header

__all__ = ('LOG_NAME', 'UnexpectedruTorrentError', 'ruTorrentClient')

#: Name used in logger.
LOG_NAME: Final[str] = 'xirvik.rutorrent'


class UnexpectedruTorrentError(Exception):
    """Raised when an unexpected error occurs."""


class ListTorrentsError(Exception):
    """Raised when ruTorrentClient.list_torrents() has an exception."""


class ruTorrentClient:
    """
    ruTorrent client class.

    `Reference on RPC returned fields.`_

    .. _Reference on RPC returned fields.: https://goo.gl/DvmW4c

    Parameters
    ==========
    host : str
        Hostname with no protocol.

    name : str | None
        Username.

        If no name and no password are passed, ``~/.netrc`` will be searched
        with the host provided. The path can be overridden with the netrc_path
        argument.

    password : str | None
        Password.

    max_retries : int
        Number of tries to retry any request.

    netrc_path : str | None
        netrc file path.

    backoff_factor : int
        Factor used to calculate back-off time when retrying requests.
    """
    def __init__(self,
                 host: str,
                 name: str | None = None,
                 password: str | None = None,
                 max_retries: int = 10,
                 netrc_path: str | None = None,
                 backoff_factor: int = 1):
        if not name and not password:
            if not netrc_path:
                netrc_path = expanduser('~/.netrc')
            netrc_data = netrc(netrc_path).authenticators(host)
            assert netrc_data is not None
            name, _, password = netrc_data
        assert name is not None
        assert password is not None
        self.name = name
        self.password = password
        self.host = host
        retry = Retry(connect=max_retries,
                      read=max_retries,
                      redirect=False,
                      backoff_factor=backoff_factor)
        self._log = logging.getLogger(LOG_NAME)
        self._http_adapter = HTTPAdapter(max_retries=cast(Any, retry))
        self._session = requests.Session()
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

    def add_torrent(self, filepath: str, start_now: bool = True) -> None:
        """Add a torrent. Use ``start_now=False`` to start paused.

        Parameters
        ----------
        filepath : str
            File path to the torrent file.

        start_now : bool
            If the torrent should start immediately.
        """
        with open(filepath, 'rb') as f:
            self._session.post(self.add_torrent_uri,
                               data=dict(torrents_start_stopped='on') if not start_now else {},
                               auth=self.auth,
                               files=dict(torrent_file=f)).raise_for_status()

    def list_torrents(self) -> Iterator[TorrentInfo]:
        """Get all torrent information."""
        r = self._session.post(self.multirpc_action_uri,
                               data=dict(mode='list', cmd='d.custom=seedingtime'),
                               auth=self.auth)
        r.raise_for_status()
        possible_dict = cast(dict[str, list[Any]], r.json()['t'])
        if not hasattr(possible_dict, 'items'):
            raise ListTorrentsError('Unexpected type in response: ' + str(type(possible_dict)))
        for hash_, x in possible_dict.items():
            del x[34]  # Delete unknown field
            for i, (type_cls, val) in enumerate(
                    zip((t[1] for t in list(TorrentInfo.__annotations__.items())[1:]),
                        (y.strip() for y in x))):
                if getattr(type_cls, '__args__', [None])[0] == datetime:
                    try:
                        x[i] = datetime.fromtimestamp(float(val or '0'))
                        # First year xirvik.com existed
                        if x[i].year < 2009:
                            x[i] = None
                    except ValueError:  # pragma no cover
                        x[i] = None
                elif type_cls == bool or issubclass(type_cls, IntEnum):
                    x[i] = type_cls(int(val))
                else:
                    x[i] = type_cls(val)
            yield TorrentInfo(hash_, *x)

    def get_torrent(self, hash_: str) -> tuple[requests.Response, str]:
        """
        Prepare to get a torrent file given a hash.

        Returns
        -------
        tuple
            ``requests.Request`` object and the file name string.
        """
        source_torrent_uri = (f'{self.http_prefix}/rtorrent/plugins/source/'
                              f'action.php?hash={hash_}')
        r = self._session.get(source_torrent_uri, auth=self.auth, stream=True)
        r.raise_for_status()
        fn = parse_header(r.headers['content-disposition'])[1]['filename']
        return r, fn

    def move_torrent(self, torrent_hash: str, target_dir: str, fast_resume: bool = True) -> None:
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
        """
        r = self._session.post(self.datadir_action_uri,
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
        if 'errors' in json and json['errors']:
            raise UnexpectedruTorrentError(str(json['errors']))

    def set_label_to_hashes(self, **kwargs: Any) -> None:
        """
        set a label to a list of info hashes. The label can be a new label.

        To remove a label, pass an empty string as the `label` keyword
        argument.

        Example use::

            client.set_labels(hashes=[hash_1, hash_2],
                              label='my new label')
        """
        # The way to set a label to multiple torrents is to specify the hashes
        # using hash=, then the v parameter as many times as there are hashes,
        # and then the s=label for as many times as there are hashes.
        # Example:
        #    mode=setlabel&hash=...&hash=...&v=label&v=label&s=label&s=label
        # This method builds this string in pieces because it is not possible to set the same key
        # twice in a dictionary.
        hashes = kwargs.pop('hashes', [])
        label = kwargs.pop('label', None)
        allow_recursive_fix = kwargs.pop('allow_recursive_fix', True)
        recursion_limit = kwargs.pop('recursion_limit', 5)
        recursion_attempt = kwargs.pop('recursion_attempt', 0)
        if not hashes or not label:
            raise TypeError('"hashes" (list) and "label" (str) keyword '
                            'arguments are required')
        data = b'mode=setlabel'
        for hash_ in hashes:
            data += f'&hash={hash_}'.encode()
        data += f'&v={label}'.encode() * len(hashes)
        data += b'&s=label' * len(hashes)
        self._log.debug('set_labels() with data: %s', data.decode())
        r = self._session.post(self.multirpc_action_uri, data=data, auth=self.auth)
        r.raise_for_status()
        json = r.json()
        # This may not be an error, but sometimes just `[]` is returned
        # Even with the retries, sometimes all but one torrent gets a label
        if len(json) != len(hashes):
            self._log.warning(
                'JSON returned should have been an array with '
                'same length as hashes list passed in: %s', json)
            if allow_recursive_fix and recursion_attempt < recursion_limit:
                recursion_attempt += 1
                self._log.info('Attempting label again '
                               '(%d out of %d)', recursion_attempt, recursion_limit)
                data = b'mode=setlabel'
                new_hashes = []
                for v in self.list_torrents():
                    hash_ = v.hash
                    if hash_ in hashes or not (v.custom1 or '').strip():
                        data += f'&hash={hash_}'.encode()
                        new_hashes.append(hash_)
                if not new_hashes:
                    self._log.debug('Found no torrents to correct')
                    return
                self.set_label_to_hashes(hashes=new_hashes,
                                         label=label,
                                         recursion_limit=recursion_limit,
                                         recursion_attempt=recursion_attempt)
            else:
                self._log.warning('Passed recursion limit for label fix')

    def set_label(self, label: str, torrent_hash: str) -> None:
        """
        set a label to a torrent.

        Parameters
        ----------
        label : str
            Label to use.
        torrent_hash : str
            Hash of the torrent.
        """
        self.set_label_to_hashes(hashes=[torrent_hash], label=label)

    def list_files(self, hash_: str) -> Iterator[TorrentTrackedFile]:
        """
        list files for a given torrent hash.

        Returns a generator of named tuples with fields (in this order):
        - name
        - total number of pieces
        - number of pieces downloaded
        - size in bytes
        - priority
        - download strategy

        Example use::

            for name, pieces, pieces_dl, size, priority, dl_strategy in \\
                client.list_files():

        Parameters
        ----------
        hash\\_ : str
            Hash of the torrent.
        """
        r = self._session.post(self.multirpc_action_uri,
                               data=(f'mode=fls&hash={hash_}' + '&' + '&'.join(f'cmd={x}' for x in (
                                   quote('f.prioritize_first='),
                                   quote('f.prioritize_last='),
                               ))),
                               auth=self.auth)
        r.raise_for_status()
        for x in r.json():
            # Fix the numeric values which come as strings
            x[1] = int(x[1])  # total number of pieces
            x[2] = int(x[2])  # downloaded pieces
            x[3] = int(x[3])  # size in bytes
            x[4] = FilePriority(int(x[4]))  # priority ID
            x[5] = FileDownloadStrategy(int(x[5]))  # download strategy ID
            # x[6] = int(x[6])  # Not used
            yield TorrentTrackedFile(*x[:6])

    def list_all_files(self) -> Iterator[TorrentTrackedFile]:
        """
        list all files tracked by rTorrent.

        If there are thousands of torrents, this may take well over 10 minutes.

        Returns a generator of tracked files.
        """
        for info in self.list_torrents():
            yield from self.list_files(info.hash)

    def delete(self, hash_: str) -> None:
        """
        Delete a torrent and its files by hash. Use the remove() method to
        remove the torrent but keep the data.

        Returns if successful. Faults are converted to xmlrpc.Fault exceptions.


        Parameters
        ----------
        hash_ : str
            Hash of the torrent.
        """
        mc = xmlrpc.MultiCall(self._xmlrpc_proxy)
        getattr(mc, 'd.custom5.set')(hash_, '1')
        getattr(mc, 'd.delete_tied')(hash_)
        getattr(mc, 'd.erase')(hash_)
        for x in mc().results:
            try:
                raise xmlrpc.Fault(
                    cast(dict[str, Any], x)['faultCode'],
                    cast(dict[str, Any], x)['faultString'])
            except (TypeError, KeyError):
                pass

    def remove(self, hash_: str) -> None:
        """
        Remove a torrent from the client but keep the data. Use the delete()
        method to remove and delete the torrent data.

        Returns if successful. Can raise a ``requests`` exception.

        Parameters
        ----------
        hash\\_ : str
            Hash of the torrent.
        """
        self._session.post(self.multirpc_action_uri,
                           data=dict(mode='remove', hash=hash_),
                           auth=self.auth).raise_for_status()

    def stop(self, hash_: str) -> None:
        """
        Stop a torrent by hash.

        Returns if successful. Can raise a ``requests`` exception.

        Parameters
        ----------
        hash\\_ : str
            Hash of the torrent.
        """
        self._session.post(self.multirpc_action_uri,
                           data=dict(mode='stop', hash=hash_),
                           auth=self.auth).raise_for_status()

    def add_torrent_url(self, url: str) -> None:
        """Add a torrent via URI.

        Parameters
        ----------
        url : str
            URI to the torrent file. Must be available either under the current
            credentials or public.
        """
        self._session.post(self.add_torrent_uri, data=dict(url=url),
                           auth=self.auth).raise_for_status()
