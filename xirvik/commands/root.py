"""The 'xirvik' command."""
import click

from .simple import (add_ftp_user, authorize_ip, delete_ftp_user, fix_rtorrent,
                     start_torrents)

# pylint: disable=invalid-name


@click.group()
def xirvik() -> None:
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
rtorrent.add_command(fix_rtorrent, 'fix')
rtorrent.add_command(start_torrents, 'add')
vm.add_command(authorize_ip)
xirvik.add_command(ftp)
xirvik.add_command(rtorrent)
xirvik.add_command(vm)
