# flake8: noqa

__title__ = 'Lavalink'
__author__ = 'Devoxin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2017-present Devoxin'
__version__ = '4.1.0'


import inspect
import logging
import sys

from .client import Client
from .errors import AuthenticationError, InvalidTrack, LoadError, NodeError
from .events import (Event, NodeChangedEvent, NodeConnectedEvent,
                     NodeDisconnectedEvent, PlayerUpdateEvent, QueueEndEvent,
                     TrackEndEvent, TrackExceptionEvent, TrackLoadFailedEvent,
                     TrackStartEvent, TrackStuckEvent, WebSocketClosedEvent)
from .filters import (ChannelMix, Equalizer, Filter, Karaoke, LowPass,
                      Rotation, Timescale, Tremolo, Vibrato, Volume)
from .models import (AudioTrack, BasePlayer, DefaultPlayer, DeferredAudioTrack,
                     LoadResult, LoadType, PlaylistInfo, Plugin, Source)
from .node import Node
from .nodemanager import NodeManager
from .playermanager import PlayerManager
from .stats import Penalty, Stats
from .utils import (decode_track, encode_track, format_time, parse_time,
                    timestamp_to_millis)


def enable_debug_logging(submodule: str = None):
    """
    Sets up a logger to stdout. This solely exists to make things easier for
    end-users who want to debug issues with Lavalink.py.

    Parameters
    ----------
    module: :class:`str`
        The module to enable logging for. ``None`` to enable debug logging for
        the entirety of Lavalink.py.

        Example: ``lavalink.enable_debug_logging('websocket')``
    """
    module_name = 'lavalink.{}'.format(submodule) if submodule else 'lavalink'
    log = logging.getLogger(module_name)

    fmt = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',  # lavalink.py
        datefmt="%H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)


def listener(*events: Event):
    """
    Marks this function as an event listener for Lavalink.py.
    This **must** be used on class methods, and you must ensure that you register
    decorated methods by using :func:`Client.add_event_hooks`.

    Example:

        .. code:: python

            @listener()
            async def on_lavalink_event(self, event):  # Event can be ANY Lavalink event
                ...

            @listener(TrackStartEvent)
            async def on_track_start(self, event: TrackStartEvent):
                ...

    Note
    ----
    Track event dispatch order is not guaranteed!
    For example, this means you could receive a :class:`TrackStartEvent` before you receive a
    :class:`TrackEndEvent` when executing operations such as ``skip()``.

    Parameters
    ----------
    events: List[:class:`Event`]
        The events to listen for. Leave this empty to listen for all events.
    """
    def wrapper(func):
        setattr(func, '_lavalink_events', events)
        return func
    return wrapper
