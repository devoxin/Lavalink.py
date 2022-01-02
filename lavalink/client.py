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
from typing import Union
from urllib.parse import quote

import aiohttp

from .errors import AuthenticationError, NodeError
from .events import Event
from .models import DefaultPlayer
from .node import Node
from .nodemanager import NodeManager
from .playermanager import PlayerManager


class Client:
    """
    Represents a Lavalink client used to manage nodes and connections.

    .. _event loop: https://docs.python.org/3/library/asyncio-eventloop.html

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
        which regions handle specific locations. Defaults to `None`.
    connect_back: Optional[:class:`bool`]
        A boolean that determines if a player will connect back to the
        node it was originally connected to. This is not recommended to do since
        the player will most likely be performing better in the new node. Defaults to `False`.

        Warning
        -------
        If this option is enabled and the player's node is changed through `Player.change_node` after
        the player was moved via the failover mechanism, the player will still move back to the original
        node when it becomes available. This behaviour can be avoided in custom player implementations by
        setting `self._original_node` to `None` in the `change_node` function.

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

        self._logger = logging.getLogger('lavalink')
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        self._user_id: str = str(user_id)
        self._connect_back: bool = connect_back
        self.node_manager: NodeManager = NodeManager(self, regions)
        self.player_manager: PlayerManager = PlayerManager(self, player)

    def add_event_hook(self, hook):
        if hook not in self._event_hooks['Generic']:
            self._event_hooks['Generic'].append(hook)

    def add_node(self, host: str, port: int, password: str, region: str,
                 resume_key: str = None, resume_timeout: int = 60, name: str = None,
                 reconnect_attempts: int = 3, filters: bool = False):
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
            Defaults to `None`.
        resume_timeout: Optional[:class:`int`]
            How long the node should wait for a connection while disconnected before clearing all players.
            Defaults to `60`.
        name: Optional[:class:`str`]
            An identifier for the node that will show in logs. Defaults to `None`
        reconnect_attempts: Optional[:class:`int`]
            The amount of times connection with the node will be reattempted before giving up.
            Set to `-1` for infinite. Defaults to `3`.
        filters: Optional[:class:`bool`]
            Whether to use the new ``filters`` op. This setting currently only applies to development
            Lavalink builds, where the ``equalizer`` op was swapped out for the broader ``filters`` op which
            offers more than just equalizer functionality. Ideally, you should only change this setting if you
            know what you're doing, as this can prevent the effects from working.
        """
        self.node_manager.add_node(host, port, password, region, resume_key, resume_timeout, name, reconnect_attempts,
                                   filters)

    async def get_tracks(self, query: str, node: Node = None):
        """|coro|
        Retrieves a list of results pertaining to the provided query.

        Parameters
        ----------
        query: :class:`str`
            The query to perform a search for.
        node: Optional[:class:`Node`]
            The node to use for track lookup. Leave this blank to use a random node.
            Defaults to `None` which is a random node.

        Returns
        -------
        :class:`dict`
            A dict representing the load response from Lavalink.
        """
        if not self.node_manager.available_nodes:
            raise NodeError('No available nodes!')
        node = node or random.choice(self.node_manager.available_nodes)
        destination = 'http://{}:{}/loadtracks?identifier={}'.format(node.host, node.port, quote(query))
        headers = {
            'Authorization': node.password
        }

        async with self._session.get(destination, headers=headers) as res:
            if res.status == 200:
                return await res.json()

            if res.status == 401 or res.status == 403:
                raise AuthenticationError

            raise NodeError('An invalid response was received from the node: code={}, body={}'
                            .format(res.status, await res.text()))

    async def decode_track(self, track: str, node: Node = None):
        """|coro|
        Decodes a base64-encoded track string into a dict.

        Parameters
        ----------
        track: :class:`str`
            The base64-encoded `track` string.
        node: Optional[:class:`Node`]
            The node to use for the query. Defaults to `None` which is a random node.

        Returns
        -------
        :class:`dict`
            A dict representing the track's information.
        """
        if not self.node_manager.available_nodes:
            raise NodeError('No available nodes!')
        node = node or random.choice(self.node_manager.available_nodes)
        destination = 'http://{}:{}/decodetrack?track={}'.format(node.host, node.port, track)
        headers = {
            'Authorization': node.password
        }

        async with self._session.get(destination, headers=headers) as res:
            if res.status == 200:
                return await res.json()

            if res.status == 401 or res.status == 403:
                raise AuthenticationError

            raise NodeError('An invalid response was received from the node: code={}, body={}'
                            .format(res.status, await res.text()))

    async def decode_tracks(self, tracks: list, node: Node = None):
        """|coro|
        Decodes a list of base64-encoded track strings into a dict.

        Parameters
        ----------
        tracks: list[:class:`str`]
            A list of base64-encoded `track` strings.
        node: Optional[:class:`Node`]
            The node to use for the query. Defaults to `None` which is a random node.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts representing track information.
        """
        if not self.node_manager.available_nodes:
            raise NodeError('No available nodes!')
        node = node or random.choice(self.node_manager.available_nodes)
        destination = 'http://{}:{}/decodetracks'.format(node.host, node.port)
        headers = {
            'Authorization': node.password
        }

        async with self._session.post(destination, headers=headers, json=tracks) as res:
            if res.status == 200:
                return await res.json()

            if res.status == 401 or res.status == 403:
                raise AuthenticationError

            raise NodeError('An invalid response was received from the node: code={}, body={}'
                            .format(res.status, await res.text()))

    async def routeplanner_status(self, node: Node):
        """|coro|
        Retrieves the status of the target node's routeplanner.

        Parameters
        ----------
        node: :class:`Node`
            The node to use for the query.

        Returns
        -------
        :class:`dict`
            A dict representing the routeplanner information.
        """
        destination = 'http://{}:{}/routeplanner/status'.format(node.host, node.port)
        headers = {
            'Authorization': node.password
        }

        async with self._session.get(destination, headers=headers) as res:
            if res.status == 200:
                return await res.json()

            if res.status == 401 or res.status == 403:
                raise AuthenticationError

            raise NodeError('An invalid response was received from the node: code={}, body={}'
                            .format(res.status, await res.text()))

    async def routeplanner_free_address(self, node: Node, address: str):
        """|coro|
        Frees up the provided IP address in the target node's routeplanner.

        Parameters
        ----------
        node: :class:`Node`
            The node to use for the query.
        address: :class:`str`
            The address to free.

        Returns
        -------
        :class:`bool`
            True if the address was freed, False otherwise.
        """
        destination = 'http://{}:{}/routeplanner/free/address'.format(node.host, node.port)
        headers = {
            'Authorization': node.password
        }

        async with self._session.post(destination, headers=headers, json={'address': address}) as res:
            return res.status == 204

    async def routeplanner_free_all_failing(self, node: Node):
        """|coro|
        Frees up all IP addresses in the target node that have been marked as failing.

        Parameters
        ----------
        node: :class:`Node`
            The node to use for the query.

        Returns
        -------
        :class:`bool`
            True if all failing addresses were freed, False otherwise.
        """
        destination = 'http://{}:{}/routeplanner/free/all'.format(node.host, node.port)
        headers = {
            'Authorization': node.password
        }

        async with self._session.post(destination, headers=headers) as res:
            return res.status == 204

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
        generic_hooks = Client._event_hooks['Generic']
        targeted_hooks = Client._event_hooks[type(event).__name__]

        if not generic_hooks and not targeted_hooks:
            return

        async def _hook_wrapper(hook, event):
            try:
                await hook(event)
            except:  # noqa: E722 pylint: disable=bare-except
                self._logger.exception('[EventDispatcher] Event hook \'{}\' encountered an exception!'.format(hook.__name__))
                #  According to https://stackoverflow.com/questions/5191830/how-do-i-log-a-python-error-with-debug-information
                #  the exception information should automatically be attached here. We're just including a message for
                #  clarity.

        tasks = [_hook_wrapper(hook, event) for hook in itertools.chain(generic_hooks, targeted_hooks)]
        await asyncio.wait(tasks)

        self._logger.debug('[EventDispatcher] Dispatched \'{}\' to all registered hooks'.format(type(event).__name__))
