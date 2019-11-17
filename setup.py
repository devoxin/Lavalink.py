import re

from setuptools import setup


version = ''
with open('lavalink/__init__.py') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

readme = ''
with open('README.md') as f:
    readme = f.read()

if not version:
    raise RuntimeError('Version is not set')

setup(
    name='lavalink',
    packages=['lavalink'],
    version=version,
    project_urls={
        "Documentation": 'https://lavalink.readthedocs.io/',
        "Issue tracker": 'https://github.com/Devoxin/Lavalink.py/issues',
    },
    description='A lavalink interface built for discord.py',
    author='Devoxin',
    author_email='luke@serux.pro',
    url='https://github.com/Devoxin/Lavalink.py',
    download_url='https://github.com/Devoxin/Lavalink.py/archive/{}.tar.gz'.format(version),
    long_description=readme,
    long_description_content_type='text/markdown',
    keywords=['lavalink'],
    license=['MIT'],
    include_package_data=True,
    install_requires=['aiohttp'],
    extras_require={'docs': ['sphinx',
                             'pygments',
                             'guzzle_sphinx_theme'],
                    'development': ['pylint',
                                    'flake8']},
    python_requires='>=3.0.0',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ]
)
