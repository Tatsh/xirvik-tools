from __future__ import print_function
from math import ceil
from os import chmod, makedirs, utime
from os.path import basename, dirname, isdir, join as path_join
import inspect
import os
import logging
import re
import socket

from paramiko.client import SSHClient
from paramiko.sftp import SFTPError
from paramiko import SFTPFile

__all__ = [
    'SFTPClient',
    'LOG_NAME',
]


LOG_NAME = 'xirvik.sftp'


class SFTPClient:
    MAX_PACKET_SIZE = SFTPFile.__dict__['MAX_REQUEST_SIZE']

    ssh_client = None
    client = None
    raise_exceptions = False
    original_arguments = {}
    debug = False

    _log = logging.getLogger(LOG_NAME)
    _dircache = []

    def __init__(self, **kwargs):
        self.original_arguments = kwargs.copy()
        self._connect(**kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()

    def _connect(self, **kwargs):
        kwargs_to_paramiko = dict(
            look_for_keys=kwargs.pop('look_for_keys', True),
            username=kwargs.pop('username'),
            port=kwargs.pop('port', 22),
            allow_agent=False,
            timeout=kwargs.pop('timeout', 10),
        )
        host = kwargs.pop('hostname', 'localhost')
        password = kwargs.pop('password')
        if password:
            kwargs_to_paramiko['password'] = password
        self.raise_exceptions = kwargs.pop('raise_exceptions', False)

        self.ssh_client = SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(host, **kwargs_to_paramiko)

        self.client = self.ssh_client.open_sftp()
        self.client.get_channel().settimeout(kwargs_to_paramiko['timeout'])

        # 'Extend' the SFTPClient class
        is_reconnect = kwargs.pop('is_reconnect', False)
        members = inspect.getmembers(self.client,
                                     predicate=inspect.ismethod)
        self._log.debug('Dynamically adding methods from original SFTPClient')
        for (method_name, method) in members:
            if method_name[0:2] == '__' or method_name == '_log':
                self._log.debug('Ignorning {}()'.format(method_name))
                continue

            if not is_reconnect and hasattr(self, method_name):
                raise AttributeError('Not overwriting property "{}". This '
                                     'version of Paramiko is not '
                                     'supported.'.format(method_name))

            self._log.debug('Adding method {}()'.format(method_name))
            setattr(self, method_name, method)

    def close_all(self):
        self.client.close()
        self.ssh_client.close()

    def clear_directory_cache(self):
        self._dircache = []

    def listdir_attr_recurse(self, path='.'):
        for da in self.client.listdir_attr(path=path):
            is_dir = da.st_mode & 0o700 == 0o700
            if is_dir:
                try:
                    yield from self.listdir_attr_recurse(
                        path_join(path, da.filename))
                except IOError as e:
                    if self.raise_exceptions:
                        raise e
            else:
                yield (path_join(path, da.filename), da,)

    def mirror(self,
               path='.',
               destroot='.',
               keep_modes=True,
               keep_times=True,
               resume=True):
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
                except FileExistsError:
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
                            self._log.info('Resuming file {} at {} '
                                           'bytes'.format(dest, current_size))
                        raise IOError()  # ugly goto
            except IOError as ioe:
                while True:
                    try:
                        # Only size is used to determine complete-ness here
                        # Hash verification is in the util module
                        if resume_seek and resume:
                            read_tuples = []

                            n_reads = ceil((info.st_size - resume_seek) / self.MAX_PACKET_SIZE) - 1
                            n_left = (info.st_size - resume_seek) % self.MAX_PACKET_SIZE
                            offset = 0

                            for n in range(n_reads):
                                read_tuples.append((resume_seek + offset, self.MAX_PACKET_SIZE,))
                                offset += self.MAX_PACKET_SIZE
                            read_tuples.append((resume_seek + offset, n_left,))

                            with self.client.open(_path) as rf:
                                with open(dest, 'ab') as f:
                                    f.seek(resume_seek)
                                    resume_seek = None

                                    for chunk in rf.readv(read_tuples):
                                        f.write(chunk)
                        else:
                            self._log.info('Downloading {} -> '
                                           '{}'.format(_path, dest))
                            self.client.get(_path, dest)

                        # Do not count files that were already downloaded
                        n += 1

                        break
                    except (socket.timeout, SFTPError) as e:
                        # Resume at position - 10 bytes
                        resume_seek = os.stat(dest).st_size - 10
                        if isinstance(e, socket.timeout):
                            self._log.error('Connection timed out')
                        else:
                            self._log.error('{!s}'.format(e))

                        if resume:
                            self._log.info('Resuming GET {} at {} '
                                           'bytes'.format(_path,
                                                          resume_seek))
                        else:
                            self._log.debug('Not resuming (resume = {}, exception: {})'.format(resume, e))
                            raise e

                        self._log.debug('Re-establishing connection')
                        self.original_arguments['is_reconnect'] = True
                        self._connect(**self.original_arguments)
                        if cwd:
                            self.chdir(cwd)

            # Okay to fix existing files even if they are already downloaded
            try:
                if keep_modes:
                    chmod(dest, info.st_mode)
                if keep_times:
                    utime(dest, (info.st_atime, info.st_mtime,))
            except IOError:
                pass

        return n

    def __str__(self):
        return '{} (wrapped by {}.SFTPClient)'.format(
            str(self.client), __name__)
    __unicode__ = __str__
