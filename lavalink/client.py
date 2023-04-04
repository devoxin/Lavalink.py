"""
MIT License

Copyright (c) 2017-present Devoxin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import asyncio
import inspect
import itertools
import logging
import random
from collections import defaultdict
from inspect import getmembers, ismethod
from typing import List, Optional, Set, Union

import aiohttp

from .abc import Source
from .events import Event
from .node import Node
from .nodemanager import NodeManager
from .player import DefaultPlayer
from .playermanager import PlayerManager
from .server import AudioTrack, LoadResult

_log = logging.getLogger(__name__)


class Client:
    """
    Represents a Lavalink client used to manage nodes and connections.

    Parameters
    ----------
    user_id: Union[:class:`int`, :class:`str`]
        The user id of the bot.
    player: Optional[:class:`BasePlayer`]
        The class that should be used for the player. Defaults to ``DefaultPlayer``.
        Do not change this unless you know what you are doing!
    regions: Optional[:class:`dict`]
        A mapping of continent -> Discord RTC regions.
        The key should be an identifier used when instantiating an node.
        The values should be a list of RTC regions that will be handled by the associated identifying key.

        Example: ``{"us": ("us-central", "us-east", "us-south", "us-west", "brazil")}``

        You should only change this if you know what you're doing and want more control over
        region groups. Defaults to ``None``.
    connect_back: Optional[:class:`bool`]
        A boolean that determines if a player will connect back to the
        node it was originally connected to. This is not recommended to do since
        the player will most likely be performing better in the new node. Defaults to ``False``.

        Warning
        -------
        If this option is enabled and the player's node is changed through `Player.change_node` after
        the player was moved via the failover mechanism, the player will still move back to the original
        node when it becomes available. This behaviour can be avoided in custom player implementations by
        setting ``self._original_node`` to ``None`` in the :func:`BasePlayer.change_node` function.

    Attributes
    ----------
    node_manager: :class:`NodeManager`
        Represents the node manager that contains all lavalink nodes.
    player_manager: :class:`PlayerManager`
        Represents the player manager that contains all the players.
    """
    __slots__ = ('_session', '_user_id', '_connect_back', '_event_hooks', 'node_manager', 'player_manager', 'sources')

    def __init__(self, user_id: Union[int, str], player=DefaultPlayer, regions: dict = None,
                 connect_back: bool = False):
        if not isinstance(user_id, (str, int)) or isinstance(user_id, bool):
            # bool has special handling because it subclasses `int`, so will return True for the first isinstance check.
            raise TypeError('user_id must be either an int or str (not {}). If the type is None, '
                            'ensure your bot has fired "on_ready" before instantiating '
                            'the Lavalink client. Alternatively, you can hardcode your user ID.'
                            .format(user_id))

        self._session: aiohttp.ClientSession = aiohttp.ClientSession()
        self._user_id: str = str(user_id)
        self._connect_back: bool = connect_back
        self._event_hooks = defaultdict(list)
        self.node_manager: NodeManager = NodeManager(self, regions)
        self.player_manager: PlayerManager = PlayerManager(self, player)
        self.sources: Set[Source] = set()

    def add_event_hook(self, *hooks, event: Event = None):
        """
        Adds one or more event hooks to be dispatched on an event.

        Note
        ----
        Track event dispatch order is not guaranteed!
        For example, this means you could receive a :class:`TrackStartEvent` before you receive a
        :class:`TrackEndEvent` when executing operations such as ``skip()``.

        Parameters
        ----------
        hooks: :class:`function`
            The hooks to register for the given event type.
            If ``event`` parameter is left empty, then it will run when any event is dispatched.
        event: :class:`Event`
            The event the hook belongs to. This will dispatch when that specific event is
            dispatched. Defaults to ``None`` which means the hook is dispatched on all events.
        """
        if event is not None and Event not in event.__bases__:
            raise TypeError('Event parameter is not of type Event or None')

        event_name = event.__name__ if event is not None else 'Generic'
        event_hooks = self._event_hooks[event_name]

        for hook in hooks:
            if not callable(hook) or not inspect.iscoroutinefunction(hook):
                raise TypeError('Hook is not callable or a coroutine')

            if hook not in event_hooks:
                event_hooks.append(hook)

    def add_event_hooks(self, cls):
        """
        Scans the provided class ``cls`` for functions decorated with :func:`listener`,
        and sets them up to process Lavalink events.

        Example:

            .. code:: python

                # Inside a class __init__ method
                self.client = lavalink.Client(...)
                self.client.add_event_hooks(self)

        Note
        ----
        Track event dispatch order is not guaranteed!
        For example, this means you could receive a :class:`TrackStartEvent` before you receive a
        :class:`TrackEndEvent` when executing operations such as ``skip()``.

        Parameters
        ----------
        cls: :class:`Class`
            An instance of a class.
        """
        methods = getmembers(cls, predicate=lambda meth: hasattr(meth, '__name__')
                             and not meth.__name__.startswith('_') and ismethod(meth)
                             and hasattr(meth, '_lavalink_events'))

        for _, listener in methods:  # _ = meth_name
            # wrapped = partial(listener, cls)
            events = listener._lavalink_events

            if events:
                for event in events:
                    self._event_hooks[event.__name__].append(listener)
            else:
                self._event_hooks['Generic'].append(listener)

    def register_source(self, source: Source):
        """
        Registers a :class:`Source` that Lavalink.py will use for looking up tracks.

        Parameters
        ----------
        source: :class:`Source`
            The source to register.
        """
        if not isinstance(source, Source):
            raise TypeError('Class \'{}\' must inherit Source!'.format(type(source.__name__)))

        self.sources.add(source)

    def add_node(self, host: str, port: int, password: str, region: str, name: str = None,
                 ssl: bool = False, session_id: Optional[str] = None):
        """
        Shortcut for :meth:`NodeManager.add_node`.

        Adds a node to Lavalink's node manager.

        Parameters
        ----------
        host: :class:`str`
            The address of the Lavalink node.
        port: :class:`int`
            The port to use for websocket and REST connections.
        password: :class:`str`
            The password used for authentication.
        region: :class:`str`
            The region to assign this node to.
        name: Optional[:class:`str`]
            An identifier for the node that will show in logs. Defaults to ``None``.
        ssl: Optional[:class:`bool`]
            Whether to use SSL for the node. SSL will use ``wss`` and ``https``, instead of ``ws`` and ``http``,
            respectively. Your node should support SSL if you intend to enable this, either via reverse proxy or
            other methods. Only enable this if you know what you're doing.
        session_id: Optional[:class:`str`]
            The ID of the session to resume. Defaults to ``None``.
            Only specify this if you have the ID of the session you want to resume.
        """
        self.node_manager.add_node(host, port, password, region, name, ssl, session_id)

    async def get_tracks(self, query: str, node: Node = None, check_local: bool = False) -> LoadResult:
        """|coro|

        Retrieves a list of results pertaining to the provided query.

        If ``check_local`` is set to ``True`` and any of the sources return a :class:`LoadResult`
        then that result will be returned, and Lavalink will not be queried.

        Warning
        -------
        Avoid setting ``check_local`` to ``True`` if you call this method from a custom :class:`Source` to avoid
        recursion issues!

        Parameters
        ----------
        query: :class:`str`
            The query to perform a search for.
        node: Optional[:class:`Node`]
            The node to use for track lookup. Leave this blank to use a random node.
            Defaults to ``None`` which is a random node.
        check_local: :class:`bool`
            Whether to also search the query on sources registered with this Lavalink client.

        Returns
        -------
        :class:`LoadResult`
        """
        if check_local:
            for source in self.sources:
                load_result = await source.load_item(self, query)

                if load_result:
                    return load_result

        node = node or random.choice(self.node_manager.nodes)
        return await node.get_tracks(query)

    async def decode_track(self, track: str, node: Node = None) -> AudioTrack:
        """|coro|

        Decodes a base64-encoded track string into a dict.

        Parameters
        ----------
        track: :class:`str`
            The base64-encoded ``track`` string.
        node: Optional[:class:`Node`]
            The node to use for the query. Defaults to ``None`` which is a random node.

        Returns
        -------
        :class:`AudioTrack`
        """
        node = node or random.choice(self.node_manager.nodes)
        return await node.decode_track(track)

    async def decode_tracks(self, tracks: List[str], node: Node = None) -> List[AudioTrack]:
        """|coro|

        Decodes a list of base64-encoded track strings into a dict.

        Parameters
        ----------
        tracks: List[:class:`str`]
            A list of base64-encoded ``track`` strings.
        node: Optional[:class:`Node`]
            The node to use for the query. Defaults to ``None`` which is a random node.

        Returns
        -------
        List[:class:`AudioTrack`]
            A list of dicts representing track information.
        """
        node = node or random.choice(self.node_manager.nodes)
        return await node.decode_tracks(tracks)

    async def voice_update_handler(self, data):
        """|coro|

        This function intercepts websocket data from your Discord library and
        forwards the relevant information on to Lavalink, which is used to
        establish a websocket connection and send audio packets to Discord.

        Example
        -------
        .. code:: python

            bot.add_listener(lavalink_client.voice_update_handler, 'on_socket_response')

        Parameters
        ----------
        data: :class:`dict`
            The payload received from Discord.
        """
        if not data or 't' not in data:
            return

        if data['t'] == 'VOICE_SERVER_UPDATE':
            guild_id = int(data['d']['guild_id'])
            player = self.player_manager.get(guild_id)

            if player:
                await player._voice_server_update(data['d'])
        elif data['t'] == 'VOICE_STATE_UPDATE':
            if int(data['d']['user_id']) != int(self._user_id):
                return

            guild_id = int(data['d']['guild_id'])
            player = self.player_manager.get(guild_id)

            if player:
                await player._voice_state_update(data['d'])

    async def _dispatch_event(self, event: Event):
        """|coro|

        Dispatches the given event to all registered hooks.

        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        generic_hooks = self._event_hooks['Generic']
        targeted_hooks = self._event_hooks[type(event).__name__]

        if not generic_hooks and not targeted_hooks:
            return

        async def _hook_wrapper(hook, event):
            try:
                await hook(event)
            except:  # noqa: E722 pylint: disable=bare-except
                _log.exception('Event hook \'%s\' encountered an exception!', hook.__name__)
                #  According to https://stackoverflow.com/questions/5191830/how-do-i-log-a-python-error-with-debug-information
                #  the exception information should automatically be attached here. We're just including a message for
                #  clarity.

        tasks = [_hook_wrapper(hook, event) for hook in itertools.chain(generic_hooks, targeted_hooks)]
        await asyncio.gather(*tasks)

        _log.debug('Dispatched \'%s\' to all registered hooks', type(event).__name__)

    def __repr__(self):
        return '<Client user_id={} nodes={} players={}>'.format(self._user_id, len(self.node_manager), len(self.player_manager))
