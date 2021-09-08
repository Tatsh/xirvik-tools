"""Module for Xirvik-specific tasks."""
from setuptools import setup

with open('README.md') as f:
    setup(
        name='xirvik-tools',
        version='0.3.1',
        author='Fa An',
        author_email='2998784916@qq.com',
        packages=['xirvik', 'xirvik.commands', 'xirvik.test'],
        url='https://github.com/Tatsh/xirvik-tools',
        license='LICENSE.txt',
        description='Command line utilities for interfacing with Xirvik.',
        long_description=f.read(),
        install_requires=[
            'Unidecode>=0.4.19',
            'argcomplete>=1.10.3',
            'benc>=2019.8.1',
            'cached-property>=1.0.0',
            'requests>=2.6.0',
            'rich>=10.1.0',
            'types-requests==2.25.6',
            'typing-extensions>=3.7.4.1',
            'urllib3>=1.26.2',
        ],
        entry_points={
            'console_scripts': [
                'xirvik-add-ftp-user = xirvik.commands:add_ftp_user',
                'xirvik-auth-ip = xirvik.commands:authorize_ip',
                'xirvik-delete-ftp-user = xirvik.commands:delete_ftp_user',
                'xirvik-delete-old = xirvik.commands.delete_old:main',
                'xirvik-fix-rtorrent = xirvik.commands:fix_rtorrent',
                'xirvik-move-by-label = xirvik.commands.move_by_label:main',
                'xirvik-move-erroneous = xirvik.commands.move_erroneous:main',
                'xirvik-start-torrents = xirvik.commands:start_torrents',
            ]
        },
        test_suite='xirvik.test',
        tests_require=['pytest', 'pytest-cov', 'requests-mock'])
