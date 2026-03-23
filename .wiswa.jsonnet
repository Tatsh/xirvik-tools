local utils = import 'utils.libjsonnet';

{
  project_name: 'xirvik-tools',
  description: 'Command line utilities for interfacing with Xirvik.',
  keywords: ['command line', 'xirvik'],
  primary_module: 'xirvik',
  version: '0.5.3',
  want_main: true,
  copilot: {
    intro: 'xirvik-tools is a set of command line tools for interfacing with Xirvik services.',
  },
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
          requests: utils.latestPypiPackageVersionCaret('requests'),
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
              'types-requests': utils.latestPypiPackageVersionCaret('types-requests'),
              'types-tabulate': utils.latestPypiPackageVersionCaret('types-tabulate'),
            },
          },
          tests+: {
            dependencies+: {
              'requests-mock': utils.latestPypiPackageVersionCaret('requests-mock'),
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
}
