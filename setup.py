from setuptools import setup

def get_requirements():
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()
    return requirements

setup(
    name='lavalink',
    packages=['lavalink'],
    version='2.0.2.9',
    description='A lavalink interface built for discord.py',
    author='Luke, William',
    author_email='dev@crimsonxv.pro',
    url='https://github.com/Devoxin/Lavalink.py',
    download_url='https://github.com/Devoxin/Lavalink.py/archive/2.0.2.9.tar.gz',
    keywords=['lavalink'],
    include_package_data=True,
    install_requires=get_requirements()
)
