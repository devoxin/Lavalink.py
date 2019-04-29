# flake8: noqa

__title__ = 'Lavalink'
__author__ = 'Devoxin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2018 Devoxin'
__version__ = '3.0.0'


import logging
import sys
from .client import Client
from .events import TrackStartEvent, TrackStuckEvent, TrackExceptionEvent, TrackEndEvent, QueueEndEvent
from .models import BasePlayer, DefaultPlayer, AudioTrack, NoPreviousTrack, InvalidTrack
from .node import Node
from .nodemanager import NodeManager
from .playermanager import PlayerManager
from .utils import format_time
from .websocket import WebSocket


def enable_debug_logging():
    """
    Sets up a logger to stdout. This solely exists to make things easier for
    end-users who want to debug issues with Lavalink.py.
    """
    log = logging.getLogger(__name__)

    fmt = logging.Formatter(
        '[%(asctime)s] [lavalink.py] [%(levelname)s] %(message)s',
        datefmt="%H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    log.addHandler(handler)

    log.setLevel(logging.DEBUG)
