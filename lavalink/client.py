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
import itertools
import logging
import random
from collections import defaultdict
from inspect import getmembers, ismethod
from typing import Set, Union
from urllib.parse import quote

import aiohttp

from .errors import AuthenticationError, NodeError
from .events import Event
from .models import DefaultPlayer, LoadResult, Source
from .node import Node
from .nodemanager import NodeManager
from .playermanager import PlayerManager

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
        A dictionary representing region -> discord endpoint. You should only
        change this if you know what you're doing and want more control over
        which regions handle specific locations. Defaults to ``None``.
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
    _event_hooks = defaultdict(list)

    def __init__(self, user_id: Union[int, str], player=DefaultPlayer, regions: dict = None,
                 connect_back: bool = False):
        if not isinstance(user_id, (str, int)) or isinstance(user_id, bool):
            # bool has special handling because it subclasses `int`, so will return True for the first isinstance check.
            raise TypeError('user_id must be either an int or str (not {}). If the type is None, '
                            'ensure your bot has fired "on_ready" before instantiating '
                            'the Lavalink client. Alternatively, you can hardcode your user ID.'
                            .format(user_id))

        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        self._user_id: str = str(user_id)
        self._connect_back: bool = connect_back
        self.node_manager: NodeManager = NodeManager(self, regions)
        self.player_manager: PlayerManager = PlayerManager(self, player)
        self.sources: Set[Source] = set()

    def add_event_hook(self, hook):
        """
        Registers a function to recieve and process Lavalink events.

        Note
        ----
        Track event dispatch order is not guaranteed!
        For example, this means you could receive a :class:`TrackStartEvent` before you receive a
        :class:`TrackEndEvent` when executing operations such as ``skip()``.

        Parameters
        ----------
        hook: :class:`function`
            The function to register.
        """
        if hook not in self._event_hooks['Generic']:
            self._event_hooks['Generic'].append(hook)

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
            raise TypeError('source must inherit from Source!')

        self.sources.add(source)

    def add_node(self, host: str, port: int, password: str, region: str,
                 resume_key: str = None, resume_timeout: int = 60, name: str = None,
                 reconnect_attempts: int = 3, filters: bool = True, ssl: bool = False):
        """
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
        resume_key: Optional[:class:`str`]
            A resume key used for resuming a session upon re-establishing a WebSocket connection to Lavalink.
            Defaults to ``None``.
        resume_timeout: Optional[:class:`int`]
            How long the node should wait for a connection while disconnected before clearing all players.
            Defaults to ``60``.
        name: Optional[:class:`str`]
            An identifier for the node that will show in logs. Defaults to ``None``.
        reconnect_attempts: Optional[:class:`int`]
            The amount of times connection with the node will be reattempted before giving up.
            Set to `-1` for infinite. Defaults to ``3``.
        filters: Optional[:class:`bool`]
            Whether to use the new ``filters`` op instead of the ``equalizer`` op.
            If you're running a build without filter support, set this to ``False``.
        ssl: Optional[:class:`bool`]
            Whether to use SSL for the node. SSL will use ``wss`` and ``https``, instead of ``ws`` and ``http``,
            respectively. Your node should support SSL if you intend to enable this, either via reverse proxy or
            other methods. Only enable this if you know what you're doing.
        """
        self.node_manager.add_node(host, port, password, region, resume_key, resume_timeout, name, reconnect_attempts,
                                   filters, ssl)

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

        if not self.node_manager.available_nodes:
            raise NodeError('No available nodes!')
        node = node or random.choice(self.node_manager.available_nodes)
        res = await self._get_request('{}/loadtracks?identifier={}'.format(node.http_uri, quote(query)),
                                      headers={'Authorization': node.password})
        return LoadResult.from_dict(res)

    async def decode_track(self, track: str, node: Node = None):
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
        :class:`dict`
            A dict representing the track's information.
        """
        if not self.node_manager.available_nodes:
            raise NodeError('No available nodes!')
        node = node or random.choice(self.node_manager.available_nodes)
        return await self._get_request('{}/decodetrack?track={}'.format(node.http_uri, track),
                                       headers={'Authorization': node.password})

    async def decode_tracks(self, tracks: list, node: Node = None):
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
        List[:class:`dict`]
            A list of dicts representing track information.
        """
        if not self.node_manager.available_nodes:
            raise NodeError('No available nodes!')
        node = node or random.choice(self.node_manager.available_nodes)

        return await self._post_request('{}/decodetracks'.format(node.http_uri),
                                        headers={'Authorization': node.password}, json=tracks)

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

    async def _get_request(self, url, **kwargs):
        async with self._session.get(url, **kwargs) as res:
            if res.status == 401 or res.status == 403:
                raise AuthenticationError

            if res.status == 200:
                return await res.json()

            raise NodeError('An invalid response was received from the node: code={}, body={}'
                            .format(res.status, await res.text()))

    async def _post_request(self, url, **kwargs):
        async with self._session.post(url, **kwargs) as res:
            if res.status == 401 or res.status == 403:
                raise AuthenticationError

            if 'json' in kwargs:
                if res.status == 200:
                    return await res.json()

                raise NodeError('An invalid response was received from the node: code={}, body={}'
                                .format(res.status, await res.text()))

            return res.status == 204

    async def _dispatch_event(self, event: Event):
        """|coro|

        Dispatches the given event to all registered hooks.

        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        generic_hooks = Client._event_hooks['Generic']
        targeted_hooks = Client._event_hooks[type(event).__name__]

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
        await asyncio.wait(tasks)

        _log.debug('Dispatched \'%s\' to all registered hooks', type(event).__name__)

    def __repr__(self):
        return '<Client user_id={} nodes={} players={}>'.format(self._user_id, len(self.node_manager), len(self.player_manager))
