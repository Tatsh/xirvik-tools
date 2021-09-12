import click

from .simple import (add_ftp_user, authorize_ip, delete_ftp_user, fix_rtorrent,
                     start_torrents)


@click.group()
def xirvik():
    pass


@click.group()
def vm():
    pass


@click.group()
def ftp():
    pass


@click.group()
def rtorrent():
    pass


vm.add_command(authorize_ip)
ftp.add_command(add_ftp_user, 'add-user')
ftp.add_command(delete_ftp_user, 'delete-user')
rtorrent.add_command(start_torrents, 'add')
rtorrent.add_command(fix_rtorrent, 'fix')
xirvik.add_command(vm)
xirvik.add_command(ftp)
xirvik.add_command(rtorrent)
