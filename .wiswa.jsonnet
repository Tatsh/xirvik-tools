local utils = import 'utils.libjsonnet';

{
  uses_user_defaults: true,
  project_name: 'xirvik-tools',
  description: 'Command line utilities for interfacing with Xirvik.',
  keywords: ['command line', 'xirvik'],
  primary_module: 'xirvik',
  version: '0.5.3',
  want_main: true,
  want_flatpak: true,
  publishing+: { flathub: 'sh.tat.xirvik-tools' },
  security_policy_supported_versions: { '0.5.x': ':white_check_mark:' },
  pyproject+: {
    project+: {
      scripts: { xirvik: 'xirvik.commands:xirvik' },
    },
    tool+: {
      poetry+: {
        dependencies+: {
          beautifulsoup4: utils.latestPypiPackageVersionCaret('beautifulsoup4'),
          fabric: utils.latestPypiPackageVersionCaret('fabric'),
          html5lib: utils.latestPypiPackageVersionCaret('html5lib'),
          keyring: utils.latestPypiPackageVersionCaret('keyring'),
          platformdirs: utils.latestPypiPackageVersionCaret('platformdirs'),
          pyyaml: utils.latestPypiPackageVersionCaret('pyyaml'),
          mutagen: utils.latestPypiPackageVersionCaret('mutagen'),
          ratelimit: utils.latestPypiPackageVersionCaret('ratelimit'),
          niquests: utils.latestPypiPackageVersionCaret('niquests'),
          anyio: utils.latestPypiPackageVersionCaret('anyio'),
          tabulate: utils.latestPypiPackageVersionCaret('tabulate'),
          unidecode: utils.latestPypiPackageVersionCaret('unidecode'),
        },
        include+: ['LaunchAgents', 'systemd'],
        group+: {
          dev+: {
            dependencies+: {
              'types-beautifulsoup4': utils.latestPypiPackageVersionCaret('types-beautifulsoup4'),
              'types-pyyaml': utils.latestPypiPackageVersionCaret('types-pyyaml'),
              'types-ratelimit': utils.latestPypiPackageVersionCaret('types-ratelimit'),
              'types-tabulate': utils.latestPypiPackageVersionCaret('types-tabulate'),
            },
          },
          tests+: {
            dependencies+: {
              'niquests-mock': utils.latestPypiPackageVersionCaret('niquests-mock'),
              'pytest-asyncio': utils.latestPypiPackageVersionCaret('pytest-asyncio'),
            },
          },
        },
      },
    },
  },
  pyinstaller+: {
    include_only: ['xirvik'],
    collect_data: ['binaryornot'],
    collect_submodules: ['xirvik'],
    test_commands: ['rtorrent --help'],
    uv_sync_args: ['--all-extras', '--all-groups'],
    vcpkg: {
      enabled: true,
      targets: {
        'windows-11-arm': {
          triplet: 'arm64-windows',
          packages: ['openssl'],
        },
      },
    },
  },
  snapcraft+: {
    apps+: {
      'xirvik-tools'+: {
        command: 'bin/xirvik',
      },
    },
  },
  flatpak+: { command: 'xirvik' },
}
