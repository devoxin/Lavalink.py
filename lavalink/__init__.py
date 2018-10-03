# flake8: noqa

__title__ = 'Lavalink'
__author__ = 'Devoxin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2018 Devoxin'
__version__ = '2.1.10'

from .AudioTrack import *
from .Client import *
from .PlayerManager import *
from .WebSocket import *
from . import Events
from . import Utils

import logging
import sys


log = logging.getLogger(__name__)

fmt = logging.Formatter(
    '[%(asctime)s] [lavalink.py] [%(levelname)s] %(message)s',
    datefmt="%H:%M:%S"
)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(fmt)
log.addHandler(handler)

log.setLevel(logging.INFO)
