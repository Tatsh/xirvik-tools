from distutils.core import setup

setup(
    name='xirvik-tools',
    version='0.0.3',
    author='Fa An',
    author_email='2998784916@qq.com',
    packages=['xirvik', 'xirvik.client'],
    url='https://github.com/Tatsh/xirvik-tools',
    license='LICENSE.txt',
    description='Xirvik (ruTorrent mostly) tools.',
    long_description=open('README.rst').read(),
    scripts=['bin/xirvik-mirror', 'bin/xirvik-start-torrents'],
    install_requires=[
        'cached-property>=1.0.0',
        'OSExtension>=0.1.5',
        'lockfile>=0.10.2',
        'requests>=2.6.0',
        'sh>=1.09',
    ],
)
