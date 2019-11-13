# flake8: noqa

__title__ = 'Lavalink'
__author__ = 'Devoxin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2019 Devoxin'
__version__ = '3.1.0'

import logging
import inspect
import sys
import functools

from .events import Event, TrackStartEvent, TrackStuckEvent, TrackExceptionEvent, TrackEndEvent, QueueEndEvent, \
    NodeConnectedEvent, NodeChangedEvent, NodeDisconnectedEvent, WebSocketClosedEvent
from .models import BasePlayer, DefaultPlayer, AudioTrack
from .utils import format_time, parse_time
from .client import Client
from .playermanager import PlayerManager
from .exceptions import NodeException, InvalidTrack, TrackNotBuilt
from .nodemanager import NodeManager
from .stats import Penalty, Stats
from .websocket import WebSocket
from .node import Node


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


def add_event_hook(*hooks, event: Event = None):
    """
    Adds an event hook to be dispatched on an event.

    Parameters
    ----------
    hooks: :class:`function`
        The hooks to register for the given event type.
        If `event` parameter is left empty, then it will run when any event is dispatched.
    event: :class:`Event`
        The event the hook belongs to. This will dispatch when that specific event is
        dispatched. Defaults to `None` which means the hook is dispatched on all events.
    """
    if event is not None and Event not in event.__bases__:
        raise TypeError('Event parameter is not of type Event or None')

    event_name = event.__name__ if event is not None else 'Generic'
    event_hooks = Client._event_hooks[event_name]

    for hook in hooks:
        if not callable(hook) or not inspect.iscoroutinefunction(hook):
            raise TypeError('Hook is not callable or a coroutine')

        if hook not in event_hooks:
            if '__arg_count' not in hook.__dict__:
                hook.__dict__['__arg_count'] = hook.__code__.co_argcount - 1 if inspect.ismethod(hook) \
                    else hook.__code__.co_argcount
            event_hooks.append(hook)


class ListenerAdapter:
    """ The base of all listener adapters. """
    def _get_hooks(self):
        funcs = [func for func in dir(self) if callable(getattr(self, func))]
        for hook in funcs:
            if not hook.startswith('__'):
                func = getattr(self, hook)
                if hasattr(func, '__event'):
                    yield func, getattr(func, '__event')


def add_adapter(adapter):
    """
    Adds the event hooks from the adapter.

    Parameters
    ----------
    adapter: :class:`ListenerAdapter`
        The listener adapter of which the event hooks are assigned to.
        Must be derived from :class:`ListenerAdapter`
    """
    if not isinstance(adapter, ListenerAdapter):
        raise TypeError('Adapter must be derived from ListenerAdapter')

    for hook, event in adapter._get_hooks():
        add_event_hook(hook, event=event)


def on(event: Event = None):
    """
    Adds an event hook when decorated with a function.

    Parameters
    ----------
    event: :class:`Event`
        The event that will dispatch the given event hook. Defaults to `None`
        which means the hook is dispatched on all events.
    """

    def decorator(func):
        if not inspect.iscoroutinefunction(func):
            raise TypeError('Hook is not a coroutine')

        func.__event = event

        # Hacky way of finding if function is in a class
        if '.' in func.__qualname__:
            func.__arg_count = func.__code__.co_argcount - 1
        else:
            func.__arg_count = func.__code__.co_argcount

        @functools.wraps(func)
        async def decorated_func(*args, **kwargs):
            return await func(*args, **kwargs)

        return decorated_func

    return decorator
