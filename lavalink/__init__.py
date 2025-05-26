# flake8: noqa

__title__ = 'Lavalink'
__author__ = 'Devoxin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2017-present Devoxin'
__version__ = '5.9.1'


from typing import Type

from .abc import *
from .client import *
from .dataio import *
from .errors import *
from .events import *
from .filters import *
from .node import *
from .nodemanager import *
from .player import *
from .playermanager import *
from .server import *
from .source_decoders import *
from .stats import *
from .utils import *


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
