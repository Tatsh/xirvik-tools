from distutils.core import setup

setup(
    name='xirvik-tools',
    version='0.0.5',
    author='Fa An',
    author_email='2998784916@qq.com',
    packages=['xirvik', 'xirvik.client'],
    url='https://github.com/Tatsh/xirvik-tools',
    license='LICENSE.txt',
    description='Xirvik (ruTorrent mostly) tools.',
    long_description=open('README.rst').read(),
    scripts=['bin/xirvik-start-torrents'],
    install_requires=[
        'bencodepy>=0.9.5',
        'cached-property>=1.0.0',
        'humanize>=0.5.1',
        'lockfile>=0.10.2',
        'OSExtension>=0.1.5',
        'paramiko>=1.17.0',
        'requests>=2.6.0',
        'Unidecode>=0.4.19',
    ],
    entry_points = {
        'console_scripts': [
            'xirvik-mirror = xirvik.mirror:main'
        ]
    }
)
