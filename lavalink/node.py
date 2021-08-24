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
from .events import Event
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
                 reconnect_attempts: int = 3, filters: bool = False):
        self._manager = manager
        self._ws = WebSocket(self, host, port, password, resume_key, resume_timeout, reconnect_attempts)

        self.host = host
        self.port = port
        self.password = password
        self.region = region
        self.name = name or '{}-{}:{}'.format(self.region, self.host, self.port)
        self.filters = filters
        self.stats = None

    @property
    def available(self):
        """ Returns whether the node is available for requests. """
        return self._ws.connected

    @property
    def _original_players(self):
        """ Returns a list of players that were assigned to this node, but were moved due to failover etc. """
        return [p for p in self._manager._lavalink.player_manager.values() if p._original_node == self]

    @property
    def players(self):
        """ Returns a list of all players on this node. """
        return [p for p in self._manager._lavalink.player_manager.values() if p.node == self]

    @property
    def penalty(self):
        """ Returns the load-balancing penalty for this node. """
        if not self.available or not self.stats:
            return 9e30

        return self.stats.penalty.total

    async def get_tracks(self, query: str):
        """|coro|
        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: :class:`str`
            The query to perform a search for.

        Returns
        -------
        :class:`dict`
            A dict representing an AudioTrack.
        """
        return await self._manager._lavalink.get_tracks(query, self)

    async def routeplanner_status(self):
        """|coro|
        Gets the routeplanner status of the target node.

        Returns
        -------
        :class:`dict`
            A dict representing the routeplanner information.
        """
        return await self._manager._lavalink.routeplanner_status(self)

    async def routeplanner_free_address(self, address: str):
        """|coro|
        Gets the routeplanner status of the target node.

        Parameters
        ----------
        address: :class:`str`
            The address to free.

        Returns
        -------
        bool
            True if the address was freed, False otherwise.
        """
        return await self._manager._lavalink.routeplanner_free_address(self, address)

    async def routeplanner_free_all_failing(self):
        """|coro|
        Gets the routeplanner status of the target node.

        Returns
        -------
        bool
            True if all failing addresses were freed, False otherwise.
        """
        return await self._manager._lavalink.routeplanner_free_all_failing(self)

    async def _dispatch_event(self, event: Event):
        """|coro|
        Dispatches the given event to all registered hooks.

        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        await self._manager._lavalink._dispatch_event(event)

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
