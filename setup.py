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
    description='A Lavalink WebSocket & API wrapper built around coverage, reliability and performance.',
    author='Devoxin',
    author_email='luke@serux.pro',
    entry_points={'console_scripts': ['lavalink = lavalink.__main__:main']},
    url='https://github.com/Devoxin/Lavalink.py',
    download_url='https://github.com/Devoxin/Lavalink.py/archive/{}.tar.gz'.format(version),
    keywords=['lavalink'],
    include_package_data=True,
    install_requires=['aiohttp>=3.8.0,<3.9.1'],  # >=3.9.0,<4 is 3.8+
    extras_require={'docs': ['sphinx',
                             'pygments',
                             'guzzle_sphinx_theme',
                             'enum_tools',
                             'sphinx_toolbox'],
                    'development': ['pylint',
                                    'flake8']}
)
