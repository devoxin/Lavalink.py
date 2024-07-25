# flake8: noqa

__title__ = 'Lavalink'
__author__ = 'Devoxin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2017-present Devoxin'
__version__ = '5.7.1'


from typing import Type

from .abc import BasePlayer, DeferredAudioTrack, Source
from .client import Client
from .dataio import DataReader, DataWriter
from .errors import (AuthenticationError, ClientError, InvalidTrack, LoadError,
                     RequestError)
from .events import (Event, IncomingWebSocketMessage, NodeChangedEvent,
                     NodeConnectedEvent, NodeDisconnectedEvent, NodeReadyEvent,
                     PlayerErrorEvent, PlayerUpdateEvent, QueueEndEvent,
                     TrackEndEvent, TrackExceptionEvent, TrackLoadFailedEvent,
                     TrackStartEvent, TrackStuckEvent, WebSocketClosedEvent)
from .filters import (ChannelMix, Distortion, Equalizer, Filter, Karaoke,
                      LowPass, Rotation, Timescale, Tremolo, Vibrato, Volume)
from .node import Node
from .nodemanager import NodeManager
from .player import DefaultPlayer
from .playermanager import PlayerManager
from .server import (AudioTrack, EndReason, LoadResult, LoadResultError,
                     LoadType, PlaylistInfo, Plugin, Severity)
from .source_decoders import DEFAULT_DECODER_MAPPING
from .stats import Penalty, Stats
from .utils import (decode_track, encode_track, format_time, parse_time,
                    timestamp_to_millis)


def listener(*events: Type[Event]):
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
    events: :class:`Event`
        The events to listen for. Leave this empty to listen for all events.
    """
    def wrapper(func):
        setattr(func, '_lavalink_events', events)
        return func
    return wrapper
