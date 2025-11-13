<!-- markdownlint-configure-file {"MD024": { "siblings_only": true } } -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Changed

- The `xirvik rtorrent add` command will no longer print to CLI if the system log flag is passed.
- Improved `list-untracked-files` algorithm for better performance.

### Added

- `ruTorrent.edit_torrents()` method for editing trackers, private flag, and comments.
- Command `xirvik rtorrent install-services` to install services for launchd and systemd.
- Command `xirvik rtorrent download-untracked-files`.

### Fixed

- Fixed parsing of host argument.

## [0.5.1] - 2025-04-19

### Changed

- Allow `-h` as an alias for `--help`.

### Fixed

- Type issues in various modules.
- Documentation fixes.

## [0.5.0] - 2024-05-21

### Added

- `move-by-label`: Added `--batch-size` option for processing torrents in batches.

### Changed

- `delete-old`: No longer checks creation date.
- `move-by-label`: Ignores empty base path.
- Removed `cached_property` dependency.
- Code modernization and fixes for Ruff linter issues.

## [0.4.5] - 2023-09-16

### Fixed

- Build issues.

## [0.4.4] - 2023-09-16

### Changed

- Moved manpage to correct location.

### Fixed

- Help text for `move-by-label` command.

## [0.4.3] - 2023-09-15

### Added

- Manpage for xirvik-tools.

### Changed

- Reorganised documentation structure.

## [0.4.2] - 2023-09-15

### Changed

- Switched to Ruff for linting.
- Added rstcheck for documentation validation.
- Improved test coverage.

## [0.4.1] - 2023-06-27

### Changed

- Switched to PyXDG for XDG directory handling.

## [0.4.0] - 2023-06-26

### Added

- Command `xirvik rtorrent list-all-files` to list all files tracked by torrents.
- Command `xirvik rtorrent list-files` to list files for specific torrents.
- Command `xirvik rtorrent list-torrents` to list all torrents.
- Command `xirvik rtorrent list-untracked-files` to list files not tracked by any torrent.
- `ruTorrent.list_all_files()` method.
- `--no-verify` flag for `rtorrent add` command.
- Configuration file support for all commands via `-C/--config` option.
- Support for YAML configuration files.

### Changed

- All commands now use Click framework.
- Improved exception handling with better error messages.
- `list_torrents()` now returns named tuples instead of dictionaries.
- `list_files()` now returns `TorrentTrackedFile` instances.
- Switched to GitHub Actions from Travis CI.

### Removed

- `xirvik-mirror` command (deprecated).
- `list_torrents_dict()` method (replaced by `list_torrents()`).
- Request-futures support.

### Fixed

- Handling of single-file torrents in various commands.
- macOS syslog compatibility.

## [0.3.1] - 2020-03-08

### Added

- `argcomplete` support for shell completion.

### Fixed

- `move-erroneous` command functionality.
- macOS syslog issues.
- Missing `name` field in typing definitions.

## [0.3.0] - 2020-02-20

### Added

- Typed dictionary for `list_torrents_dict()` results.
- `typing-extensions` dependency for better type hints.
- Comprehensive docstrings throughout the codebase.

### Changed

- Dropped Python 3.6 support, minimum version is now Python 3.8.
- Switched to `notpeter/benc` for bencode parsing.
- Improved type annotations throughout.

## [0.2.2] - 2020-01-20

### Fixed

- Build directory handling.

## [0.2.1] - 2019-12-17

### Added

- Command `xirvik vm authorize-ip` to authorize IP for VM SSH access.
- Command `xirvik ftp add-user` to add FTP users.
- Command `xirvik ftp delete-user` to delete FTP users.
- Command `xirvik ftp list-users` to list FTP users.
- Command `xirvik rtorrent fix` to fix rTorrent issues.
- Command `xirvik rtorrent move-by-label` to move torrents by label.
- Command `xirvik rtorrent delete-old` to delete old torrents.
- Command `xirvik rtorrent move-erroneous` to move errored torrents.
- `ruTorrent.authorize_ip()` method for VM SSH authorization.
- argcomplete dependency for shell completion.

### Changed

- Reorganized commands into subcommands: `ftp`, `rtorrent`, and `vm`.
- Improved Python 3 compatibility.
- Removed `asctime` from log formatting.

### Fixed

- `--ignore-labels` argument in `move-by-label` command.
- Certificate verification for self-signed certificates.

## [0.1.0] - 2016-05-29

### Added

- `ruTorrent.list_files()` method to list files in torrents.
- `ruTorrent.add_torrent()` method to add torrents.
- `ruTorrent.delete()` method to delete torrents with data.
- `ruTorrent.remove()` method to remove torrents without deleting data.
- `ruTorrent.stop_torrent()` method to stop torrents.
- `ruTorrent.get_torrents_futures()` method for async operations.
- `ruTorrent.list_torrents_dict()` method to get torrent information.
- Travis CI integration.
- Basic test suite.
- Coveralls integration for code coverage.

### Changed

- Moved `xirvik-start-torrents` to entry point.
- Improved logging with statistics every 60 seconds during downloads.
- Better error handling and logging.
- netrc support for authentication.

### Fixed

- Python 3 compatibility issues.
- Label setting reliability.
- Lock file handling for concurrent runs.

## [0.0.5] - 2016-03-18

### Added

- Torrent content verification against piece hashes.
- Resume capability for interrupted downloads.
- `ruTorrent.set_label_to_hashes()` method to set labels on multiple torrents.
- Keep-alive for SFTP connections.
- Bencodepy dependency for torrent file parsing.
- Humanize dependency for human-readable output.

### Changed

- Replaced `lftp` with Paramiko for SFTP operations.
- Support for single-file torrents.
- Better handling of file permissions and timestamps.
- Improved retry logic with `--max-retries` argument.

### Fixed

- Unicode filename handling with unidecode.
- Small file verification in single pieces.
- Python 2 compatibility issues.
- Resumption of downloads after interruption.

## [0.0.4] - 2015-12-29

### Added

- Example systemd service and timer files.
- Example launchd property list.

### Changed

- Improved error handling for label setting.
- Better logging for mirror operations.

## [0.0.3] - 2015-12-04

### Added

- urllib3 dependency with retry support.
- HTTPAdapter with configurable max retries.

### Changed

- Improved reliability of HTTP requests with retry logic.

## [0.0.2] - 2015-04-05

### Added

- Lock file handling based on unique argument hashing.
- `ruTorrent.get_torrent_file()` method to download torrent files.

### Fixed

- OS X and BSD compatibility.

## [0.0.1] - 2015-04-05

### Added

- Initial release.
- `ruTorrent` client class for interacting with ruTorrent.
- `xirvik-mirror` script for syncing files.
- Basic logging facilities.
- Signal handling for graceful shutdown.
- `ruTorrent.set_label()` method.
- `ruTorrent.move_torrent()` method.

[unreleased]: https://github.com/Tatsh/xirvik-tools/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/Tatsh/xirvik-tools/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Tatsh/xirvik-tools/compare/v0.4.5...v0.5.0
[0.4.5]: https://github.com/Tatsh/xirvik-tools/compare/v0.4.4...v0.4.5
[0.4.4]: https://github.com/Tatsh/xirvik-tools/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/Tatsh/xirvik-tools/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/Tatsh/xirvik-tools/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/Tatsh/xirvik-tools/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/Tatsh/xirvik-tools/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Tatsh/xirvik-tools/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Tatsh/xirvik-tools/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/Tatsh/xirvik-tools/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/Tatsh/xirvik-tools/compare/v0.1.0...v0.2.1
[0.1.0]: https://github.com/Tatsh/xirvik-tools/compare/v0.0.5...v0.1.0
[0.0.5]: https://github.com/Tatsh/xirvik-tools/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/Tatsh/xirvik-tools/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/Tatsh/xirvik-tools/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/Tatsh/xirvik-tools/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/Tatsh/xirvik-tools/releases/tag/v0.0.1
