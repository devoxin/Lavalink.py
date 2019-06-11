# flake8: noqa

__title__ = 'Lavalink'
__author__ = 'Devoxin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2019 Devoxin'
__version__ = '3.0.0'


import logging
import sys
from .client import Client
from .events import Event, TrackStartEvent, TrackStuckEvent, TrackExceptionEvent, TrackEndEvent, QueueEndEvent
from .models import BasePlayer, DefaultPlayer, AudioTrack, NoPreviousTrack, InvalidTrack
from .node import Node
from .nodemanager import NodeManager
from .playermanager import PlayerManager
from .utils import format_time
from .websocket import WebSocket

_internal_event_hooks = {}


def enable_debug_logging():
    """
    Sets up a logger to stdout. This solely exists to make things easier for
    end-users who want to debug issues with Lavalink.py.
    """
    log = logging.getLogger('lavalink')

    fmt = logging.Formatter(
        '[%(asctime)s] [lavalink.py] [%(levelname)s] %(message)s',
        datefmt="%H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    log.addHandler(handler)

    log.setLevel(logging.DEBUG)


def _internal_add_event_hook(hook, event: Event = None):
    """
    Adds an event hook to be dispatched on an event.
    ----------
    :param hook:
        The hook to be added, that will be dispatched when an event is dispatched.
        If `event` parameter is left empty, then it will run when any event is dispatched.
    :param event:
        The event the hook belongs to. This will dispatch when that specific event is
        dispatched.
    """
    event_hooks = _internal_event_hooks.get(event)

    if hook not in event_hooks:
        if not event_hooks:
            _internal_event_hooks['Generic'] = [hook]
        else:
            _internal_event_hooks[event].append(hook)


def on(event: Event = 'Generic'):
    """
    Adds an event hook when decorated with a function.

    Parameters
    ----------
    event: Event
        The event that will dispatch the given event hook. This defaults
        to 'Generic', which is dispatched on all events.
    """
    def decorator(func):
        _internal_add_event_hook(func, event)

    return decorator
