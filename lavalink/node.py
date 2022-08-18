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
from typing import List

from lavalink.models import Plugin

from .events import Event
from .stats import Stats
from .websocket import WebSocket


class Node:
    """
    Represents a Node connection with Lavalink.

    Note
    ----
    Nodes are **NOT** mean't to be added manually, but rather with :func:`Client.add_node`. Doing this can cause
    invalid cache and much more problems.

    Attributes
    ----------
    host: :class:`str`
        The address of the Lavalink node.
    port: :class:`int`
        The port to use for websocket and REST connections.
    password: :class:`str`
        The password used for authentication.
    ssl: :class:`bool`
        Whether this node uses SSL (wss/https).
    region: :class:`str`
        The region to assign this node to.
    name: :class:`str`
        The name the :class:`Node` is identified by.
    filters: :class:`bool`
        Whether or not to use the new ``filters`` op instead of ``equalizer``.
        This setting is only used by players.
    stats: :class:`Stats`
        The statistics of how the :class:`Node` is performing.
    """
    def __init__(self, manager, host: str, port: int, password: str,
                 region: str, resume_key: str, resume_timeout: int, name: str = None,
                 reconnect_attempts: int = 3, filters: bool = False, ssl: bool = False):
        self._lavalink = manager._lavalink
        self._manager = manager
        self._ws = WebSocket(self, host, port, password, ssl, resume_key, resume_timeout, reconnect_attempts)

        self.host = host
        self.port = port
        self.password = password
        self.ssl = ssl
        self.region = region
        self.name = name or '{}-{}:{}'.format(self.region, self.host, self.port)
        self.filters = filters
        self.stats = Stats.empty(self)

    @property
    def available(self) -> bool:
        """ Returns whether the node is available for requests. """
        return self._ws.connected

    @property
    def _original_players(self):
        """
        Returns a list of players that were assigned to this node, but were moved due to failover etc.

        Returns
        -------
        List[:class:`BasePlayer`]
        """
        return [p for p in self._lavalink.player_manager.values() if p._original_node == self]

    @property
    def players(self):
        """
        Returns a list of all players on this node.

        Returns
        -------
        List[:class:`BasePlayer`]
        """
        return [p for p in self._lavalink.player_manager.values() if p.node == self]

    @property
    def penalty(self) -> int:
        """ Returns the load-balancing penalty for this node. """
        if not self.available or not self.stats:
            return 9e30

        return self.stats.penalty.total

    @property
    def http_uri(self) -> str:
        """ Returns a 'base' URI pointing to the node's address and port, also factoring in SSL. """
        return '{}://{}:{}'.format('https' if self.ssl else 'http', self.host, self.port)

    async def destroy(self):
        """|coro|

        Closes the WebSocket connection for this node. No further connection attempts will be made.
        """
        await self._ws.destroy()

    async def get_tracks(self, query: str, check_local: bool = False):
        """|coro|

        Retrieves a list of results pertaining to the provided query.

        Parameters
        ----------
        query: :class:`str`
            The query to perform a search for.
        check_local: :class:`bool`
            Whether to also search the query on sources registered with this Lavalink client.

        Returns
        -------
        :class:`LoadResult`
        """
        return await self._lavalink.get_tracks(query, self, check_local)

    async def routeplanner_status(self):
        """|coro|

        Retrieves the status of the target node's routeplanner.

        Returns
        -------
        :class:`dict`
            A dict representing the routeplanner information.
        """
        return await self._lavalink._get_request('{}/routeplanner/status'.format(self.http_uri),
                                                 headers={'Authorization': self.password})

    async def routeplanner_free_address(self, address: str) -> bool:
        """|coro|

        Frees up the provided IP address in the target node's routeplanner.

        Parameters
        ----------
        address: :class:`str`
            The address to free.

        Returns
        -------
        :class:`bool`
            True if the address was freed, False otherwise.
        """
        return await self._lavalink._post_request('{}/routeplanner/free/address'.format(self.http_uri),
                                                  headers={'Authorization': self.password}, json={'address': address})

    async def routeplanner_free_all_failing(self) -> bool:
        """|coro|

        Frees up all IP addresses in the target node that have been marked as failing.

        Returns
        -------
        :class:`bool`
            True if all failing addresses were freed, False otherwise.
        """
        return await self._lavalink._post_request('{}/routeplanner/free/all'.format(self.http_uri),
                                                  headers={'Authorization': self.password})

    async def get_plugins(self) -> List[Plugin]:
        """|coro|

        Retrieves a list of plugins active on this node.

        Returns
        -------
        List[:class:`Plugin`]
            A list of active plugins.
        """
        data = await self._lavalink._get_request('{}/plugins'.format(self.http_uri),
                                                 headers={'Authorization': self.password})
        return [Plugin(plugin) for plugin in data]

    async def _dispatch_event(self, event: Event):
        """|coro|

        Dispatches the given event to all registered hooks.

        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        await self._lavalink._dispatch_event(event)

    async def _send(self, **data):
        """|coro|

        Sends the passed data to the node via the websocket connection.

        Parameters
        ----------
        data: class:`any`
            The dict to send to Lavalink.
        """
        await self._ws._send(**data)

    def __repr__(self):
        return '<Node name={0.name} region={0.region}>'.format(self)
