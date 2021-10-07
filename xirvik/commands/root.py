"""The 'xirvik' command."""
from typing import Optional

import click

from .delete_old import main as delete_old
from .move_by_label import main as move_by_label
from .move_erroneous import main as move_erroneous
from .simple import (add_ftp_user, authorize_ip, delete_ftp_user, fix_rtorrent,
                     list_ftp_users, start_torrents)
from .util import complete_hosts

__all__ = ('xirvik',)

# pylint: disable=invalid-name,unused-argument


@click.group()
@click.option('-C', '--config', help='Configuration file')
@click.option('-H',
              '--host',
              help='Xirvik host (without protocol)',
              shell_complete=complete_hosts)
def xirvik(config: Optional[str] = None, host: Optional[str] = None) -> None:
    """Root command."""


@click.group()
def vm() -> None:
    """Commands for the Linux virtual machine."""


@click.group()
def ftp() -> None:
    """Commands for managing the FTP server."""


@click.group()
def rtorrent() -> None:
    """Commands for managing rTorrent."""


ftp.add_command(add_ftp_user, 'add-user')
ftp.add_command(delete_ftp_user, 'delete-user')
ftp.add_command(list_ftp_users, 'list-users')
rtorrent.add_command(start_torrents, 'add')
rtorrent.add_command(delete_old, 'delete-old')
rtorrent.add_command(fix_rtorrent, 'fix')
rtorrent.add_command(move_by_label, 'move-by-label')
rtorrent.add_command(move_erroneous, 'move-erroneous')
vm.add_command(authorize_ip)
xirvik.add_command(ftp)
xirvik.add_command(rtorrent)
xirvik.add_command(vm)
