# To use

1. Edit a copy of this file for use filling in the path to the script (with full path to Python 3.4+ if necessary), server host, and path to search.
2. Add the port argument (`-P`) if necessary.
3. Add any other arguments you would like _except_ `-d` (debug) or `-v` (verbose).
4. If you plan to use this as a user and not as a system service, copy both the timer and service file to `~/.config/systemd/user/`. If you plan to use this as a system service, copy both the timer and service file to `/etc/systemd/system/` (must be root).
5. To enable and start a user: `systemctl --user enable xirvik-start-torrents.timer`, `systemctl --user start xirvik-start-torrents.timer`. If as system, run as root and use: `systemctl enable xirvik-start-torrents.timer`, `systemctl start xirvik-start-torrents.timer`.
