"""Module for Xirvik-specific tasks."""
from setuptools import setup

setup(
    name='xirvik-tools',
    version='0.2.0',
    author='Fa An',
    author_email='2998784916@qq.com',
    packages=['xirvik'],
    url='https://github.com/Tatsh/xirvik-tools',
    license='LICENSE.txt',
    description='Xirvik (ruTorrent mostly) tools.',
    long_description=open('README.md').read(),
    install_requires=[
        'bencodepy>=0.9.5',
        'cached-property>=1.0.0',
        'humanize>=0.5.1',
        'lockfile>=0.10.2',
        'paramiko>=1.17.0',
        'requests>=2.6.0',
        'six>=1.10.0',
        'Unidecode>=0.4.19',
    ],
    entry_points={
        'console_scripts': [
            'xirvik-mirror = xirvik.commands:mirror_main',
            'xirvik-start-torrents = xirvik.commands:start_torrents',
        ]
    },
    test_suite='xirvik.test',
    tests_require=['coveralls', 'nose', 'requests-mock'])
