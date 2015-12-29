from cgi import parse_header
import logging

from cached_property import cached_property
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util import Retry
import requests


__all__ = [
    'LOG_NAME',
    'TORRENT_PATH_INDEX',
    'UnexpectedruTorrentError',
    'ruTorrentClient',
]

LOG_NAME = 'xirvik-rutorrent'
TORRENT_PATH_INDEX = 25


class UnexpectedruTorrentError(Exception):
    pass


class ruTorrentClient:
    host = None
    name = None
    password = None
    _log = logging.getLogger(LOG_NAME)
    _http_adapter = None
    _session = None

    def __init__(self, host, name, password, max_retries=10):
        self.host = host
        self.name = name
        self.password = password
        retry = Retry(connect=max_retries,
                      read=max_retries,
                      redirect=False,
                      backoff_factor=1)
        self._http_adapter = HTTPAdapter(max_retries=retry)
        self._session = requests.Session()
        self._session.mount('http://', self._http_adapter)
        self._session.mount('https://', self._http_adapter)

    @cached_property
    def http_prefix(self):
        return 'https://{host:s}'.format(host=self.host)

    @cached_property
    def multirpc_action_uri(self):
        return ('{}/rtorrent/plugins/multirpc/'
                'action.php'.format(self.http_prefix))

    @cached_property
    def datadir_action_uri(self):
        return ('{}/rtorrent/plugins/datadir/'
                'action.php'.format(self.http_prefix))

    @cached_property
    def _add_torrent_uri(self):
        return '{}/rtorrent/php/addtorrent.php?'.format(host=self.host)

    @cached_property
    def auth(self):
        return (self.name, self.password,)

    def add_torrent(self, filepath, start_now=True):
        data = {}

        if not start_now:
            data['torrents_start_stopped'] = 'on'

        with open(filepath, 'rb') as f:
            files = dict(torrent_file=f)
            r = self._session.post(self._add_torrent_uri,
                              data=data,
                              auth=self.auth,
                              files=files)

            r.raise_for_status()

    def list_torrents(self):
        data = {
            'mode': 'list',
            'cmd': 'd.custom=addtime',
        }
        r = self._session.post(self.multirpc_action_uri, data=data, auth=self.auth)

        r.raise_for_status()

        return r.json()['t']

    def get_torrent(self, hash):
        source_torrent_uri = ('{}/rtorrent/plugins/source/action.php'
                              '?hash={}'.format(self.http_prefix, hash))

        r = self._session.get(self.source_torrent_uri, auth=self.auth, stream=True)

        r.raise_for_status()

        fn = parse_header(r.headers['content-disposition'])[1]['filename']

        return r, fn

    def move_torrent(self, hash, target_dir, fast_resume=True):
        data = {
            'hash': hash,
            'datadir': target_dir,
            'move_addpath': '1',
            'move_datafiles': '1',
            'move_fastresume': '1' if fast_resume else '0',
        }
        r = self._session.post(self.datadir_action_uri, data=data, auth=self.auth)

        r.raise_for_status()

        json = r.json()

        if 'errors' in json and len(json['errors']):
            raise UnexpectedruTorrentError(str(json['errors']))

    def set_label(self, hash, label):
        data = {
            'mode': 'setlabel',
            'hash': hash,
            'v': label,
            's': 'label',
        }
        r = self._session.post(self.multirpc_action_uri, data=data, auth=self.auth)

        r.raise_for_status()
