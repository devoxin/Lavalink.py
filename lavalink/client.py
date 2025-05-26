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
import logging
import random
from collections import defaultdict
from inspect import getmembers, ismethod
from typing import (Any, Callable, Coroutine, Dict, Final, Generic, Optional,
                    Sequence, Set, Tuple, Type, TypeVar, Union)

import aiohttp

from .abc import BasePlayer, Source
from .common import VoiceServerUpdatePayload, VoiceStateUpdatePayload
from .errors import ClientError
from .events import Event
from .node import Node
from .nodemanager import NodeManager
from .player import DefaultPlayer
from .playermanager import PlayerManager
from .server import AudioTrack, LoadResult

__all__ = (
    "Client",
)

_log = logging.getLogger(__name__)

PlayerT = TypeVar('PlayerT', bound=BasePlayer)
EventT = TypeVar('EventT', bound=Event)


class Client(Generic[PlayerT]):
    """
    Represents a Lavalink client used to manage nodes and connections.

    Parameters
    ----------
    user_id: Union[:class:`int`, :class:`str`]
        The user id of the bot.
    player: Type[:class:`BasePlayer`]
        The class that should be used for the player. Defaults to :class:`DefaultPlayer`.
        Do not change this unless you know what you are doing!
    regions: Optional[Dict[str, Tuple[str]]]
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
    request_timeout: Optional[:class:`aiohttp.ClientTimeout`]
        A ``ClientTimeout`` object to be used for requests. If unspecified, defaults will be used.

    Attributes
    ----------
    node_manager: :class:`NodeManager`
        The node manager, used for storing and managing all registered Lavalink nodes.
    player_manager: :class:`PlayerManager`
        The player manager, used for storing and managing all players.
    sources: Set[:class:`Source`]
        The custom sources registered to this client.
    """
    __slots__ = ('_session', '_user_id', '_event_hooks', 'node_manager', 'player_manager', 'sources')

    def __init__(self, user_id: Union[int, str], player: Type[PlayerT] = DefaultPlayer,
                 regions: Optional[Dict[str, Tuple[str]]] = None, connect_back: bool = False,
                 request_timeout: Optional[aiohttp.ClientTimeout] = None):
        if not isinstance(user_id, (str, int)) or isinstance(user_id, bool):
            # bool has special handling because it subclasses `int`, so will return True for the first isinstance check.
            raise TypeError(f'user_id must be either an int or str (not {type(user_id).__name__}). '
                            'If the type is None, ensure your bot has fired "on_ready" before instantiating '
                            'the Lavalink client. Alternatively, you can hardcode your user ID.')

        self._session: Final[aiohttp.ClientSession] = aiohttp.ClientSession(timeout=request_timeout)
        self._user_id: Final[int] = int(user_id)
        self._event_hooks: Final[dict[str, list]] = defaultdict(list)
        self.node_manager: Final[NodeManager] = NodeManager(self, regions, connect_back)
        self.player_manager: Final[PlayerManager[PlayerT]] = PlayerManager(self, player)
        self.sources: Final[Set[Source]] = set()

    @property
    def nodes(self) -> Sequence[Node]:
        """
        Convenience shortcut for :attr:`NodeManager.nodes`.
        """
        return self.node_manager.nodes

    @property
    def players(self) -> Dict[int, PlayerT]:
        """
        Convenience shortcut for :attr:`PlayerManager.players`.
        """
        return self.player_manager.players

    async def close(self):
        """|coro|

        Closes all active connections and frees any resources in use.
        """
        for node in self.node_manager:
            await node.destroy()

        await self._session.close()

    def add_event_hook(self, *hooks, event: Optional[Type[EventT]] = None):
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
        event: Optional[Type[:class:`Event`]]
            The event the hooks belong to. They will be called when that specific event type is
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

    def add_event_hooks(self, cls: object):
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
        cls: object
            An instance of a class containing event hook methods.
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

    def remove_event_hooks(self, *, events: Optional[Sequence[Type[EventT]]] = None, hooks: Sequence[Callable]):
        """
        Removes the given hooks from the event hook registry.

        Parameters
        ----------
        events: Sequence[:class:`Event`]
            The events to remove the hooks from. This parameter can be omitted,
            and the events registered on the function via :func:`listener` will be used instead, if applicable.
            Otherwise, a default value of ``Generic`` is used instead.
        hooks: Sequence[Callable]
            A list of hook methods to remove.
        """
        if events is not None:
            for event in events:
                if Event not in event.__bases__:
                    raise TypeError(f'{event.__name__} is not of type Event')

        for hook in hooks:
            if not callable(hook):
                raise ValueError(f'Provided hook {hook} is not a callable')

        for hook in hooks:
            unregister_events = events or getattr(hook, '_lavalink_events', None)

            try:
                if not unregister_events:
                    self._event_hooks['Generic'].remove(hook)
                else:
                    for event in unregister_events:
                        self._event_hooks[event.__name__].remove(hook)
            except ValueError:
                pass

    def register_source(self, source: Source):
        """
        Registers a :class:`Source` that Lavalink.py will use for looking up tracks.

        Parameters
        ----------
        source: :class:`Source`
            The source to register.
        """
        if not isinstance(source, Source):
            raise TypeError(f'Class \'{type(source).__name__}\' must inherit Source!')

        self.sources.add(source)

    def get_source(self, source_name: str) -> Optional[Source]:
        """
        Gets a registered source by the given name.

        Parameters
        ----------
        source_name: :class:`str`
            The name of the source to get.

        Returns
        -------
        Optional[:class:`Source`]
            The source with the matching name. May be ``None`` if
            the name didn't match any of those in the registered sources.
        """
        return next((source for source in self.sources if source.name == source_name), None)

    def add_node(self, host: str, port: int, password: str, region: str, name: Optional[str] = None,
                 ssl: bool = False, session_id: Optional[str] = None, connect: bool = True,
                 tags: Optional[Dict[str, Any]] = None) -> Node:
        """
        Shortcut for :func:`NodeManager.add_node`.

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
        ssl: :class:`bool`
            Whether to use SSL for the node. SSL will use ``wss`` and ``https``, instead of ``ws`` and ``http``,
            respectively. Your node should support SSL if you intend to enable this, either via reverse proxy or
            other methods. Only enable this if you know what you're doing.
        session_id: Optional[:class:`str`]
            The ID of the session to resume. Defaults to ``None``.
            Only specify this if you have the ID of the session you want to resume.
        connect: :class:`bool`
            Whether to immediately connect to the node after creating it.
            If ``False``, you must call :func:`Node.connect` if you require WebSocket functionality.
        tags: Optional[Dict[:class:`str`, Any]]
            Additional tags to attach to this node. You can use this to store additional metadata
            that you may need to access later.

        Returns
        -------
        :class:`Node`
            The created Node instance.
        """
        return self.node_manager.add_node(host, port, password, region, name, ssl,
                                          session_id, connect, tags)

    async def get_local_tracks(self, query: str) -> LoadResult:
        """|coro|

        Searches :attr:`sources` registered to this client for the given query.

        Parameters
        ----------
        query: :class:`str`
            The query to perform a search for.

        Returns
        -------
        :class:`LoadResult`
        """
        for source in self.sources:
            load_result = await source.load_item(self, query)

            if load_result:
                return load_result

        return LoadResult.empty()

    async def get_tracks(self, query: str, node: Optional[Node] = None,
                         check_local: bool = False) -> LoadResult:
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

        Raises
        ------
        :class:`ClientError`
            If there are no nodes assigned to this client.

        Returns
        -------
        :class:`LoadResult`
        """
        if check_local:
            for source in self.sources:
                load_result = await source.load_item(self, query)

                if load_result:
                    return load_result

        if not node:
            available_nodes = self.node_manager.available_nodes

            if available_nodes:
                node = random.choice(available_nodes)
            elif self.node_manager.nodes:
                node = random.choice(self.node_manager.nodes)
            else:
                raise ClientError('No available nodes!')

        return await node.get_tracks(query)

    async def decode_track(self, track: str, node: Optional[Node] = None) -> AudioTrack:
        """|coro|

        Decodes a base64-encoded track string into a dict.

        Parameters
        ----------
        track: :class:`str`
            The base64-encoded ``track`` string.
        node: Optional[:class:`Node`]
            The node to use for the query. Defaults to ``None`` which is a random node.

        Raises
        ------
        :class:`ClientError`
            If there are no nodes assigned to this client.

        Returns
        -------
        :class:`AudioTrack`
        """
        if not node:
            available_nodes = self.node_manager.available_nodes

            if available_nodes:
                node = random.choice(available_nodes)
            elif self.node_manager.nodes:
                node = random.choice(self.node_manager.nodes)
            else:
                raise ClientError('No available nodes!')

        return await node.decode_track(track)

    async def decode_tracks(self, tracks: Sequence[str], node: Optional[Node] = None) -> Sequence[AudioTrack]:
        """|coro|

        Decodes a list of base64-encoded track strings into a list of :class:`AudioTrack`.

        Parameters
        ----------
        tracks: Sequence[:class:`str`]
            A list of base64-encoded ``track`` strings.
        node: Optional[:class:`Node`]
            The node to use for the query. Defaults to ``None`` which is a random node.

        Raises
        ------
        :class:`ClientError`
            If there are no nodes assigned to this client.

        Returns
        -------
        Sequence[:class:`AudioTrack`]
            A list of decoded :class:`AudioTrack`.
        """
        if not node:
            available_nodes = self.node_manager.available_nodes

            if available_nodes:
                node = random.choice(available_nodes)
            elif self.node_manager.nodes:
                node = random.choice(self.node_manager.nodes)
            else:
                raise ClientError('No available nodes!')

        return await node.decode_tracks(tracks)

    async def voice_update_handler(self, data: Union[VoiceStateUpdatePayload, VoiceServerUpdatePayload]):
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
        data: Dict[str, Any]
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
            if int(data['d']['user_id']) != self._user_id:
                return

            guild_id = int(data['d']['guild_id'])
            player = self.player_manager.get(guild_id)

            if player:
                await player._voice_state_update(data['d'])

    def has_listeners(self, event: Type[Event]) -> bool:
        """
        Check whether the client has any listeners for a specific event type.
        """
        return len(self._event_hooks['Generic']) > 0 or len(self._event_hooks[event.__name__]) > 0

    def _dispatch_event(self, event: Event):
        """
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

        hooks = generic_hooks + targeted_hooks
        loop = asyncio.get_event_loop()
        loop.create_task(self.__real_dispatch(event, hooks))

    async def __real_dispatch(self, event: Event, hooks: Sequence[Callable[[Event], Coroutine[Any, Any, Any]]]):
        async def _hook_wrapper(hook, event):
            try:
                await hook(event)
            except asyncio.CancelledError:
                _log.debug('Event hook \'%s\' dispatch was cancelled.', hook.__name__)
            except:  # noqa: E722 pylint: disable=bare-except
                _log.exception('Event hook \'%s\' encountered an exception!', hook.__name__)

        tasks = [_hook_wrapper(hook, event) for hook in hooks]
        await asyncio.gather(*tasks)
        _log.debug('Dispatched \'%s\' to all registered hooks', type(event).__name__)

    def __repr__(self):
        return f'<Client user_id={self._user_id} nodes={len(self.node_manager)} players={len(self.player_manager)}>'
