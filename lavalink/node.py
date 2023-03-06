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

from .abc import BasePlayer
from .errors import RequestError
from .server import AudioTrack, LoadResult, Plugin
from .stats import Stats
from .transport import Transport


class Node:
    """
    Represents a Node connection with Lavalink.

    Note
    ----
    To construct a node, you should use :func:`Client.add_node` instead.

    Attributes
    ----------
    region: :class:`str`
        The region to assign this node to.
    name: :class:`str`
        The name the :class:`Node` is identified by.
    stats: :class:`Stats`
        The statistics of how the :class:`Node` is performing.
    """
    def __init__(self, manager, host: str, port: int, password: str, region: str, name: str = None,
                 ssl: bool = False):
        self.client = manager.client
        self.manager = manager
        self._transport = Transport(self, host, port, password, ssl)

        self.region: str = region
        self.name: str = name or '{}-{}:{}'.format(region, host, port)
        self.stats: Stats = Stats.empty(self)

    @property
    def available(self) -> bool:
        """
        Returns whether the node is available for requests.

        .. deprecated:: 5.0.0
            As of Lavalink server 4.0.0, a WebSocket connection is no longer required to operate a
            node. As a result, this property is no longer considered useful.
        """
        return True

    @property
    def _original_players(self) -> List[BasePlayer]:
        """
        Returns a list of players that were assigned to this node, but were moved due to failover etc.

        Returns
        -------
        List[:class:`BasePlayer`]
        """
        return [p for p in self.client.player_manager.values() if p._original_node == self]

    @property
    def players(self) -> List[BasePlayer]:
        """
        Returns a list of all players on this node.

        Returns
        -------
        List[:class:`BasePlayer`]
        """
        return [p for p in self.client.player_manager.values() if p.node == self]

    @property
    def penalty(self) -> int:
        """ Returns the load-balancing penalty for this node. """
        if not self.available or not self.stats:
            return 9e30

        return self.stats.penalty.total

    async def destroy(self):
        """|coro|

        Destroys the transport and any underlying connections for this node.
        This will also cleanly close the websocket.
        """
        await self._transport.close()

    async def get_tracks(self, query: str) -> LoadResult:
        """|coro|

        Retrieves a list of results pertaining to the provided query.

        Parameters
        ----------
        query: :class:`str`
            The query to perform a search for.

        Returns
        -------
        :class:`LoadResult`
        """
        return await self._transport._get_request('/loadtracks', params={'identifier': query}, to=LoadResult)

    async def decode_track(self, track: str) -> AudioTrack:
        """|coro|

        Decodes a base64-encoded track string into an :class:`AudioTrack` object.

        Parameters
        ----------
        track: :class:`str`
            The base64-encoded track string to decode.

        Returns
        -------
        :class:`AudioTrack`
        """
        return await self._transport._get_request('/decodetrack', params={'track': track}, to=AudioTrack)

    async def decode_tracks(self, tracks: List[str]) -> List[AudioTrack]:
        """|coro|

        Decodes a list of base64-encoded track strings into a list of :class:`AudioTrack`.

        Parameters
        ----------
        tracks: List[:class:`str`]
            A list of base64-encoded ``track`` strings.

        Returns
        -------
        List[:class:`AudioTrack`]
            A list of decoded AudioTracks.
        """
        response = await self._transport._post_request('/decodetracks', json=tracks)
        return list(map(AudioTrack, response))

    async def routeplanner_status(self):
        """|coro|

        Retrieves the status of the target node's routeplanner.

        Returns
        -------
        :class:`dict`
            A dict representing the routeplanner information.
        """
        return await self._transport._get_request('/routeplanner/status')

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
        try:
            return await self._transport._post_request('/routeplanner/free/address', json={'address': address})
        except RequestError:
            return False

    async def routeplanner_free_all_failing(self) -> bool:
        """|coro|

        Frees up all IP addresses in the target node that have been marked as failing.

        Returns
        -------
        :class:`bool`
            True if all failing addresses were freed, False otherwise.
        """
        try:
            return await self._transport._post_request('/routeplanner/free/all')
        except RequestError:
            return False

    async def get_plugins(self) -> List[Plugin]:
        """|coro|

        Retrieves a list of plugins active on this node.

        Returns
        -------
        List[:class:`Plugin`]
            A list of active plugins.
        """
        return list(map(Plugin, await self._transport._get_request('/plugins')))

    def __repr__(self):
        return '<Node name={0.name} region={0.region}>'.format(self)
