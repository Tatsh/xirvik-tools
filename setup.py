"""Module for Xirvik-specific tasks."""
from setuptools import setup

with open('README.md') as f:
    setup(
        name='xirvik-tools',
        version='2.0.0',
        author='Fa An',
        author_email='2998784916@qq.com',
        packages=['xirvik', 'xirvik.commands'],
        url='https://github.com/Tatsh/xirvik-tools',
        license='LICENSE.txt',
        description='Command line utilities for interfacing with Xirvik.',
        long_description=f.read(),
        install_requires=[
            'Unidecode>=0.4.19',
            'cached-property>=1.0.0',
            'click>=8.0.0',
            'loguru>=0.5.3',
            'requests>=2.6.0',
            'types-requests==2.25.6',
            'typing-extensions>=3.7.4.1',
            'urllib3>=1.26.2',
        ],
        entry_points={'console_scripts': [
            'xirvik = xirvik.commands:xirvik',
        ]},
        extras_require={
            'testing':
            ['mock', 'pytest', 'pytest-cov', 'pytest-mock', 'requests-mock']
        })
