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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .abc import BasePlayer, Filter
from .errors import ClientError, RequestError
from .server import AudioTrack, LoadResult
from .stats import Stats
from .transport import Transport

if TYPE_CHECKING:
    from .client import Client
    from .nodemanager import NodeManager


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
        self.client: 'Client' = manager.client
        self.manager: 'NodeManager' = manager
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
        return await self._transport._request('GET', '/loadtracks', params={'identifier': query}, to=LoadResult)

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
        return await self._transport._request('GET', '/decodetrack', params={'track': track}, to=AudioTrack)

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
        response = await self._transport._request('POST', '/decodetracks', json=tracks)
        return list(map(AudioTrack, response))

    async def get_routeplanner_status(self) -> Dict[str, Any]:
        """|coro|

        Retrieves the status of the target node's routeplanner.

        Returns
        -------
        Dict[str, Any]
            A dict representing the routeplanner information.
        """
        return await self._transport._request('GET', '/routeplanner/status')

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
            return await self._transport._request('POST', '/routeplanner/free/address', json={'address': address})
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
            return await self._transport._request('POST', '/routeplanner/free/all')
        except RequestError:
            return False

    async def get_info(self) -> Dict[str, Any]:
        """|coro|

        Retrieves information about this node.

        Returns
        -------
        Dict[str, Any]
            A raw response containing information about the node.
        """
        return await self._transport._request('GET', '/info')

    async def get_stats(self) -> Dict[str, Any]:
        """|coro|

        Retrieves statistics about this node.

        Returns
        -------
        Dict[str, Any]
            A raw response containing information about the node.
        """
        return await self._transport._request('GET', '/stats')

# TODO: Special handling for this, as it's not JSON. Also, this doesn't require a versioned route.
    # async def get_version(self) -> str:
    #     """|coro|

    #     Retrieves the version of this node.

    #     Returns
    #     -------
    #     str
    #         The version of this Lavalink server.
    #     """
    #     return await self._transport._request('GET', '/stats')

    async def get_player(self, guild_id: Union[str, int]) -> Dict[str, Any]:
        """|coro|

        Retrieves a player from the node.
        This returns raw data, to retrieve a player you can interact with, use :meth:`PlayerManager.get`.

        Returns
        -------
        Dict[str, Any]
            A raw player object.
        """
        session_id = self._transport.session_id

        if not session_id:
            raise ClientError('Cannot retrieve a player without a valid session ID!')

        return await self._transport._request('GET', '/sessions/{}/players/{}'.format(session_id, guild_id))

    async def get_players(self) -> List[Dict[str, Any]]:
        """|coro|

        Retrieves a list of players from the node.
        This returns raw data, to retrieve players you can interact with, use :attr:`players`.

        Returns
        -------
        List[Dict[str, Any]]
            A list of raw player objects.
        """
        session_id = self._transport.session_id

        if not session_id:
            raise ClientError('Cannot retrieve a list of players without a valid session ID!')

        return await self._transport._request('GET', '/sessions/{}/players'.format(session_id))

    async def update_player(self, guild_id: Union[str, int], no_replace: Optional[bool] = None,  # pylint: disable=too-many-locals
                            encoded_track: Optional[str] = '', identifier: Optional[str] = None,
                            position: Optional[int] = None, end_time: Optional[int] = None,
                            volume: Optional[int] = None, paused: Optional[bool] = None,
                            filters: Optional[List[Filter]] = None, voice_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """|coro|

        Update the state of a player.

        Parameters
        ----------
        guild_id: Union[str, int]
            The guild ID of the player to update.
        no_replace: Optional[bool]
            Whether to replace the currently playing track with the new track.
        encoded_track: Optional[str]
            The base64-encoded track string to play.
            You may provide ``None`` to stop the player.

            Warning
            -------
            This option is mutually exclusive with ``identifier``. You cannot provide both options.
        identifier: Optional[str]
            The identifier of the track to play. This can be a track ID or URL. It may not be a
            search query or playlist link. If it yields a search, playlist, or no track, a :class:`RequestError`
            will be raised.

            Warning
            -------
            This option is mutually exclusive with ``encoded_track``. You cannot provide both options.
        position: Optional[int]
            The track position in milliseconds. This can be used to seek.
        end_time: Optional[int]
            The position, in milliseconds, to end the track at.
        volume: Optional[int]
            The new volume of the player. This must be within the range of 0 to 1000.
        paused: Optional[bool]
            Whether to pause the player.
        filters: Optional[List[:class:`Filter`]]
            The filters to apply to the player.
        voice_state: Optional[Dict[str, Any]]
            The new voice state of the player.

        Returns
        -------
        Dict[str, Any]
            A raw player object.
        """
        # TODO: Update the cached player if identifier, encoded_track or filters are specified.
        session_id = self._transport.session_id

        if not session_id:
            raise ClientError('Cannot update the state of a player without a valid session ID!')

        if encoded_track and identifier:
            raise ValueError('encoded_track and identifier are mutually exclusive options, you may not specify both together.')

        params = {}
        json = {}

        if no_replace is not None and isinstance(no_replace, bool):
            params['noReplace'] = str(no_replace).lower()

        if identifier is not None:
            if not isinstance(identifier, str):
                raise ValueError('identifier must be a str!')

            json['identifier'] = identifier
        else:
            if encoded_track is not None and not isinstance(encoded_track, str):
                raise ValueError('encoded_track must be either be a str or None!')

            if encoded_track is None or len(encoded_track) > 0:
                json['encodedTrack'] = encoded_track

        if position is not None:
            if not isinstance(position, (int, float)):
                raise ValueError('position must be an int!')

            json['position'] = position

        if end_time is not None:
            if not isinstance(end_time, int) or end_time <= 0:
                raise ValueError('end_time must be an int, and greater than 0!')

            json['endTime'] = end_time

        if volume is not None:
            if not isinstance(volume, int) or not 0 <= volume <= 1000:
                raise ValueError('volume must be an int, and within the range of 0 to 1000!')

            json['volume'] = volume

        if paused is not None:
            if not isinstance(paused, bool):
                raise ValueError('paused must be a bool!')

            json['paused'] = paused

        if filters is not None:
            if not isinstance(filters, list) or not all(isinstance(f, Filter) for f in filters):
                raise ValueError('filters must be a list of Filter!')

            serialized = {}
            for f in filters:
                serialized.update(f.serialize())

            json['filters'] = serialized

        if voice_state is not None:
            if not isinstance(voice_state, dict):
                raise ValueError('voice_state must be a dict!')

            json['voice'] = voice_state

        if not json:
            return

        return await self._transport._request('PATCH', '/sessions/{}/players/{}'.format(session_id, guild_id),
                                              params=params, json=json)

    async def destroy_player(self, guild_id: Union[str, int]) -> bool:
        """|coro|

        Destroys a player on the node.
        It's recommended that you use :meth:`PlayerManager.destroy` to destroy a player.

        Returns
        -------
        bool
            Whether the player was destroyed.
        """
        session_id = self._transport.session_id

        if not session_id:
            raise ClientError('Cannot destroy a player without a valid session ID!')

        return await self._transport._request('DELETE', '/sessions/{}/players/{}'.format(session_id, guild_id))

    async def update_session(self, resuming: Optional[bool] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """|coro|

        Update the session for this node.

        Parameters
        ----------
        resuming: Optional[bool]
            Whether to enable resuming for this session or not.
        timeout: Optional[int]
            How long the node will wait for the session to resume before destroying it, in seconds.

        Returns
        -------
        Dict[str, Any]
            A raw response from the node containing the current session configuration.
        """
        session_id = self._transport.session_id

        if not session_id:
            raise ClientError('Cannot update a session without a valid session ID!')

        json = {}

        if resuming is not None:
            if not isinstance(resuming, bool):
                raise ValueError('resuming must be a bool!')

            json['resuming'] = resuming

        if timeout is not None:
            if not isinstance(timeout, int) or timeout <= 0:
                raise ValueError('timeout must be an int greater than 0!')

            json['timeout'] = timeout

        if not json:
            return

        return await self._transport._request('PATCH', '/sessions/{}'.format(session_id), json=json)

    def __repr__(self):
        return '<Node name={0.name} region={0.region}>'.format(self)

# TODO: update_session() perhaps belongs in client.
