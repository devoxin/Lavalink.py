from setuptools import setup


setup(
    name='lavalink',
    packages=['lavalink'],
    version='3.0.0',
    description='A lavalink interface built for discord.py',
    author='Devoxin',
    author_email='luke@serux.pro',
    url='https://github.com/Devoxin/Lavalink.py',
    # download_url='https://github.com/Devoxin/Lavalink.py/archive/3.0.0.tar.gz',
    keywords=['lavalink'],
    include_package_data=True,
    install_requires=['websockets>=5.0.1,<6.1.0', 'aiohttp']
)
