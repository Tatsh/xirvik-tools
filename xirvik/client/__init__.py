from cgi import parse_header
from netrc import netrc
from os.path import expanduser
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

LOG_NAME = 'xirvik.rutorrent'

TORRENT_PIECE_SIZE_INDEX = 13
TORRENT_LABEL_INDEX = 14
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

    def __init__(self,
                 host,
                 name=None,
                 password=None,
                 max_retries=10,
                 **kwargs):
        if not name and not password:
            nrc_path = kwargs.pop('netrc_path', expanduser('~/.netrc'))
            name, _, password = netrc(nrc_path).authenticators(host)

        self.name = name
        self.password = password

        self.host = host
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
        r = self._session.post(self.multirpc_action_uri,
                               data=data,
                               auth=self.auth)

        r.raise_for_status()

        return r.json()['t']

    def get_torrent(self, hash):
        source_torrent_uri = ('{}/rtorrent/plugins/source/action.php'
                              '?hash={}'.format(self.http_prefix, hash))

        r = self._session.get(source_torrent_uri,
                              auth=self.auth,
                              stream=True)

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
        r = self._session.post(self.datadir_action_uri,
                               data=data,
                               auth=self.auth)

        r.raise_for_status()

        json = r.json()

        if 'errors' in json and len(json['errors']):
            raise UnexpectedruTorrentError(str(json['errors']))

    def set_label_to_hashes(self, **kwargs):
        """
        Set a label to a list of info hashes. The label can be a new label.

        To remove a label, pass an empty string as the `label` keyword
        argument.

        Example use:
            client.set_labels(hashes=[hash_1, hash_2], label='my new label')
        """
        # The way to set a label to multiple torrents is to specify the hashes
        # using hash=, then the v parameter as many times as there are hashes,
        # and then the s=label for as many times as there are hashes.
        #
        # Example:
        #    mode=setlabel&hash=...&hash=...&v=label&v=label&s=label&s=label
        #
        # This method builds this string out since Requests can take in a byte
        # string as POST data (and you cannot set a key twice in a dictionary).
        hashes = kwargs.pop('hashes', [])
        label = kwargs.pop('label', None)
        allow_recursive_fix = kwargs.pop('allow_recursive_fix', True)
        recursion_limit = kwargs.pop('recursion_limit', 5)
        recursion_attempt = kwargs.pop('recursion_attempt', 0)

        if not hashes or not label:
            raise TypeError('"hashes" (list) and "label" (str) keyword '
                            'arguments are required')

        data = b'mode=setlabel'

        for hash in hashes:
            data += '&hash={}'.format(hash).encode('utf-8')

        data += '&v={}'.format(label).encode('utf-8') * len(hashes)
        data += b'&s=label' * len(hashes)
        self._log.debug('set_labels() with data: {}'.format(
            data.decode('utf-8')))

        r = self._session.post(self.multirpc_action_uri,
                               data=data,
                               auth=self.auth)
        r.raise_for_status()
        json = r.json()

        # This may not be an error, but sometimes just `[]` is returned
        if len(json) != len(hashes):
            self._log.warning('JSON returned should have been an '
                              'array with same length as hashes '
                              'list passed in: {}'.format(json))

            if allow_recursive_fix and recursion_attempt < recursion_limit:
                recursion_attempt += 1

                self._log.info('Attempting label again '
                               '({:d} out of {:d})'.format(recursion_attempt,
                                                            recursion_limit))

                data = b'mode=setlabel'
                new_hashes = []

                for hash, v in self.list_torrents().items():
                    if hash not in hashes or v[TORRENT_LABEL_INDEX].strip():
                        continue

                    data += '&hash={}'.format(hash).encode('utf-8')
                    new_hashes.append(hash)

                if not new_hashes:
                    self._log.debug('Found no torrents to correct')
                    return

                self.set_label_to_hashes(hashes=new_hashes,
                                         label=label,
                                         recursion_limit=recursion_limit,
                                         recursion_attempt=recursion_attempt)
            else:
                self._log.warning('Passed recursion limit for label fix')

    def set_label(self, label, hash):
        data = {
            'mode': 'setlabel',
            'hash': hash,
            'v': label,
            's': 'label',
        }

        r = self._session.post(self.multirpc_action_uri,
                               data=data,
                               auth=self.auth)
        r.raise_for_status()
        last_json = r.json()

        if label not in last_json:
            raise UnexpectedruTorrentError('Did not find label in JSON: '
                                           '{}'.format(last_json))
