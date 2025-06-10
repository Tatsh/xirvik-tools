(import 'defaults.libjsonnet') + {
  // Project-specific
  description: 'Command line utilities for interfacing with Xirvik.',
  keywords: ['command line', 'xirvik'],
  project_name: 'xirvik-tools',
  version: '0.5.1',
  want_main: true,
  primary_module: 'xirvik',
  citation+: {
    'date-released': '2025-04-17',
  },
  pyproject+: {
    project+: {
      include+: ['LaunchAgents', 'man', 'systemd'],
      scripts: { xirvik: 'xirvik.commands:xirvik' },
    },
    tool+: {
      poetry+: {
        dependencies+: {
          beautifulsoup4: '^4.13.4',
          'cached-property': '^2.0.1',
          html5lib: '^1.1',
          keyring: '^25.6.0',
          platformdirs: '^4.3.8',
          pyyaml: '^6.0.2',
          mutagen: '^1.47.0',
          ratelimit: '^2.2.1',
          requests: '^2.32.4',
          tabulate: '^0.9.0',
          unidecode: '^1.4.0',
        },
        include+: ['LaunchAgents', 'systemd'],
        group+: {
          dev+: {
            dependencies+: {
              'ratelimit-types': '^0',
              'types-beautifulsoup4': '^4.12.0.20250516',
              'types-pyyaml': '^6.0.12.20250516',
              'types-requests': '^2.32.0.20250602',
              'types-tabulate': '^0.9.0.20241207',
            },
          },
          tests+: {
            dependencies+: {
              'requests-mock': '^1.12.1',
            },
          },
        },
      },
    },
  },
  // Common
  authors: [
    {
      'family-names': 'Udvare',
      'given-names': 'Andrew',
      email: 'audvare@gmail.com',
      name: '%s %s' % [self['given-names'], self['family-names']],
    },
  ],
  local funding_name = '%s2' % std.asciiLower(self.github_username),
  github_username: 'Tatsh',
  github+: {
    funding+: {
      ko_fi: funding_name,
      liberapay: funding_name,
      patreon: funding_name,
    },
  },
}
