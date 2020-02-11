import re

from setuptools import setup


version = ''
with open('lavalink/__init__.py') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Version is not set')

setup(
    name='lavalink',
    packages=['lavalink'],
    version=version,
    description='A lavalink interface built for discord.py',
    author='Devoxin',
    author_email='luke@serux.pro',
    url='https://github.com/Devoxin/Lavalink.py',
    download_url='https://github.com/Devoxin/Lavalink.py/archive/{}.tar.gz'.format(version),
    keywords=['lavalink'],
    include_package_data=True,
    install_requires=['aiohttp>=3.6.0,<3.7.0'],
    extras_require={'docs': ['sphinx',
                             'pygments',
                             'guzzle_sphinx_theme'],
                    'development': ['pylint',
                                    'flake8']}
)
