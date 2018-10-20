#!/usr/bin/env python
"""
Example script to move torrents based on their label set in ruTorrent.

./move-by-label.py USERNAME HOSTNAME [PATH]
"""
from __future__ import print_function
from time import sleep
import sys

from xirvik.client import ruTorrentClient

USERNAME = sys.argv[1]
HOST = sys.argv[2]
try:
    PATH = sys.argv[3]
except IndexError:
    PATH = ''
PREFIX = '/torrents/{}/{}'.format(USERNAME, PATH)

if __name__ == '__main__':
    client = ruTorrentClient(HOST)
    count = 0

    for hash, info in client.list_torrents_dict().iteritems():
        name = info['name'].encode('utf-8')
        label = info['custom1']
        move_to = '{}/{}'.format(PREFIX, label.lower())

        # Ignore torrents that are hash checking, not finished hash checking,
        # not complete or that are already moved
        if (info['is_hash_checking'] or not info['is_hash_checked']
                or info['left_bytes'] > 0
                or info['base_path'].startswith(move_to)):
            continue

        print('Moving {} to {}/'.format(name, move_to.encode('utf-8'), name))
        client.move_torrent(hash, move_to)

        # Sometimes the web server cannot handle so many requests, so only
        # send 10 at a time
        count += 1
        if count and (count % 10) == 0:
            sleep(10)
