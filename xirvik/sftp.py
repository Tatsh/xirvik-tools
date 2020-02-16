"""SFTP client like paramiko's with extra features."""
from datetime import datetime
from math import ceil, floor
from os import chmod, makedirs, utime
from os.path import basename, dirname, isdir, join as path_join, realpath
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, cast
import inspect
import logging
import os
import socket

from humanize import naturaldelta, naturalsize
from paramiko import SFTPAttributes, SFTPClient as OriginalSFTPClient, SFTPFile
from paramiko.client import SSHClient
from paramiko.sftp import SFTPError

from .typing import Method0, Method1

__all__ = (
    'SFTPClient',
    'LOG_NAME',
)

LOG_NAME = 'xirvik.sftp'
LOG_INTERVAL = 60


class SFTPClient:
    """Dynamic extension on paramiko's SFTPClient."""
    chdir: Method1['SFTPClient', str, Optional[str]]
    getcwd: Method0['SFTPClient', str]
    listdir_iter: Callable[..., Iterator[Any]]

    MAX_PACKET_SIZE: int = SFTPFile.__dict__['MAX_REQUEST_SIZE']

    original_arguments: Dict[str, Any] = {}
    debug: bool = False

    _log = logging.getLogger(LOG_NAME)
    _dircache: List[str] = []

    def __init__(self, **kwargs: Any):
        """Constructor."""
        self.original_arguments = kwargs.copy()
        self._connect(**kwargs)

    def __enter__(self) -> 'SFTPClient':
        """For use with a with statement."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """For use with a with statement."""
        self.close_all()

    def _connect(self, **kwargs: Any) -> None:
        kwargs_to_paramiko = dict(
            look_for_keys=kwargs.pop('look_for_keys', True),
            username=kwargs.pop('username'),
            port=kwargs.pop('port', 22),
            allow_agent=False,
            timeout=kwargs.pop('timeout', None),
        )
        host = kwargs.pop('hostname', 'localhost')
        password = kwargs.pop('password')
        keepalive = kwargs.pop('keepalive', 5)
        if password:
            kwargs_to_paramiko['password'] = password
        self.raise_exceptions: bool = kwargs.pop('raise_exceptions', False)
        self.ssh_client = SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(host, **kwargs_to_paramiko)
        self.client: OriginalSFTPClient = self.ssh_client.open_sftp()
        channel = self.client.get_channel()
        channel.settimeout(kwargs_to_paramiko['timeout'])
        channel.get_transport().set_keepalive(keepalive)
        # 'Extend' the SFTPClient class
        is_reconnect: bool = kwargs.pop('is_reconnect', False)
        members = inspect.getmembers(self.client, predicate=inspect.ismethod)
        self._log.debug('Dynamically adding methods from original SFTPClient')
        for method_name, method in members:
            if method_name[0:2] == '__' or method_name == '_log':
                self._log.debug('Ignoring %s()', method_name)
                continue
            if not is_reconnect and hasattr(self, method_name):
                raise AttributeError('Not overwriting property "{}". This '
                                     'version of Paramiko is not '
                                     'supported.'.format(method_name))
            self._log.debug('Adding method %s()', method_name)
            setattr(self, method_name, method)

    def close_all(self) -> None:
        """Close client and SSH client handles."""
        self.client.close()
        self.ssh_client.close()

    def clear_directory_cache(self) -> None:
        """Reset directory cache."""
        self._dircache = []

    def listdir_attr_recurse(self,
                             path: str = '.'
                             ) -> Iterator[Tuple[str, SFTPAttributes]]:
        """List directory attributes recursively."""
        for dir_attr in self.client.listdir_attr(path=path):
            is_dir = dir_attr.st_mode & 0o700 == 0o700
            if is_dir:
                try:
                    for x in self.listdir_attr_recurse(
                            path_join(path, dir_attr.filename)):
                        yield x
                except IOError as e:
                    if self.raise_exceptions:
                        raise e
            else:
                yield (
                    path_join(path, dir_attr.filename),
                    dir_attr,
                )

    def _get_callback(self, start_time: datetime,
                      _log: logging.Logger) -> Callable[[int, int], None]:
        def cb(tx_bytes: int, total_bytes: int) -> None:
            total_time = datetime.now() - start_time
            total_time_total_secs = total_time.total_seconds()
            total_time_s = floor(total_time_total_secs)

            if (total_time_s % LOG_INTERVAL) != 0:
                return

            nsize_tx = naturalsize(tx_bytes, binary=True, format='%.2f')
            nsize_total = naturalsize(total_bytes, binary=True, format='%.2f')

            speed_in_s = tx_bytes / total_time_total_secs
            speed_in_s = naturalsize(speed_in_s, binary=True, format='%.2f')

            _log.info('Downloaded %s / %s in %s (%s/s)', nsize_tx, nsize_total,
                      naturaldelta(datetime.now() - start_time), speed_in_s)

        return cb

    def mirror(self,
               path: str = '.',
               destroot: str = '.',
               keep_modes: bool = True,
               keep_times: bool = True,
               resume: bool = True) -> int:
        """
        Mirror a remote directory to a local location.

        path is the remote directory. destroot must be the location where
        destroot/path will be created (the path must not already exist).

        keep_modes and keep_times are boolean to ensure permissions and time
        are retained respectively.

        Pass resume=False to disable file resumption.
        """
        n = 0
        resume_seek = None
        cwd = self.getcwd()
        for _path, info in self.listdir_attr_recurse(path=path):
            if info.st_mode & 0o700 == 0o700:
                continue
            dest_path = path_join(destroot, dirname(_path))
            dest = path_join(dest_path, basename(_path))
            if dest_path not in self._dircache:
                try:
                    makedirs(dest_path)
                except OSError:
                    pass
                self._dircache.append(dest_path)
            if isdir(dest):
                continue
            try:
                with open(dest, 'rb'):
                    current_size = os.stat(dest).st_size
                    if current_size != info.st_size:
                        resume_seek = current_size
                        if resume:
                            self._log.info('Resuming file %s at %s bytes',
                                           dest, current_size)
                        raise IOError()  # ugly goto
            except IOError:
                while True:
                    try:
                        # Only size is used to determine complete-ness here
                        # Hash verification is in the util module
                        if resume_seek and resume:
                            read_tuples = []
                            n_reads = ceil((info.st_size - resume_seek) /
                                           self.MAX_PACKET_SIZE) - 1
                            n_left = ((info.st_size - resume_seek) %
                                      self.MAX_PACKET_SIZE)
                            offset = 0
                            for n in range(n_reads):
                                read_tuples.append((
                                    resume_seek + offset,
                                    self.MAX_PACKET_SIZE,
                                ))
                                offset += self.MAX_PACKET_SIZE
                            read_tuples.append((
                                resume_seek + offset,
                                n_left,
                            ))
                            with self.client.open(_path) as sftp_file:
                                with open(dest, 'ab') as f:
                                    f.seek(resume_seek)
                                    resume_seek = None
                                    for chunk in sftp_file.readv(read_tuples):
                                        f.write(chunk)
                        else:
                            dest = realpath(dest)
                            self._log.info('Downloading %s -> %s', _path, dest)
                            start_time = datetime.now()
                            self.client.get(_path, dest)
                            self._get_callback(start_time,
                                               self._log)(info.st_size,
                                                          info.st_size)

                        # Do not count files that were already downloaded
                        n += 1

                        break
                    except (socket.timeout, SFTPError) as e:
                        # Resume at position - 10 bytes
                        resume_seek = os.stat(dest).st_size - 10
                        if isinstance(e, socket.timeout):
                            self._log.error('Connection timed out')
                        else:
                            self._log.error('%s', e)
                        if resume:
                            self._log.info('Resuming GET %s at %s bytes',
                                           _path, resume_seek)
                        else:
                            self._log.debug(
                                'Not resuming (resume = %s, exception: %s)',
                                resume, e)
                            raise e
                        self._log.debug('Re-establishing connection')
                        self.original_arguments['is_reconnect'] = True
                        self._connect(**self.original_arguments)
                        if cwd:
                            cast(OriginalSFTPClient, self).chdir(cwd)
            # Okay to fix existing files even if they are already downloaded
            try:
                if keep_modes:
                    chmod(dest, info.st_mode)
                if keep_times:
                    utime(dest, (
                        info.st_atime,
                        info.st_mtime,
                    ))
            except IOError:
                pass
        return n

    def __str__(self) -> str:
        """Return string representation."""
        return f'{self.client} (wrapped by {__name__}.SFTPClient)'
