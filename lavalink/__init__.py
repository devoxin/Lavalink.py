__title__ = 'Lavalink'
__author__ = 'Luke & William'
__license__ = 'MIT'
__copyright__ = 'Copyright 2018 Luke & William'
__version__ = '2.0.2.9'

from .audio_track import *
from .client import *
from .player_manager import *
from .utils import *
from .websocket import *
from .events import *

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
