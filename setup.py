'''Module for Xirvik-specific tasks.'''
from distutils.cmd import Command
import subprocess as sp

from setuptools import setup


class BuildDocumentationCommand(Command):
    '''A custom command to generate documentation with Sphinx.'''

    description = 'Generate documentation.'
    user_options = [('type=', 'M', 'type of documentation')]

    def initialize_options(self) -> None:
        self.type = 'help'

    def finalize_options(self) -> None:
        pass

    def run(self) -> None:
        sp.run(('sphinx-build', '-M', self.type, 'doc', 'build'), check=True)


with open('README.md') as f:
    setup(
        author='Fa An',
        author_email='2998784916@qq.com',
        cmdclass={'build_docs': BuildDocumentationCommand},
        description='Command line utilities for interfacing with Xirvik.',
        entry_points={'console_scripts': ['xirvik = xirvik.commands:xirvik']},
        extras_require={
            'dev': ['rope'],
            'testing':
            ['mock', 'pytest', 'pytest-cov', 'pytest-mock', 'requests-mock']
        },
        install_requires=[
            'Unidecode>=0.4.19',
            'cached-property>=1.0.0',
            'click>=8.0.0',
            'loguru>=0.5.3',
            'PyYAML>=5.4.1',
            'requests>=2.6.0',
            'types-requests==2.25.9',
            'typing-extensions>=3.7.4.1',
            'urllib3>=1.26.2',
            'xdg>=5.1.1',
        ],
        license='LICENSE.txt',
        long_description=f.read(),
        name='xirvik-tools',
        packages=['xirvik', 'xirvik.commands'],
        url='https://github.com/Tatsh/xirvik-tools',
        version='2.0.0')
