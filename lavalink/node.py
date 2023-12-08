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
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, overload

from .abc import BasePlayer, Filter
from .common import MISSING
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
    client: :class:`Client`
        The Lavalink client.
    region: :class:`str`
        The region to assign this node to.
    name: :class:`str`
        The name the :class:`Node` is identified by.
    stats: :class:`Stats`
        The statistics of how the :class:`Node` is performing.
    """
    __slots__ = ('client', 'manager', '_transport', 'region', 'name', 'stats')

    def __init__(self, manager, host: str, port: int, password: str, region: str, name: str = None,
                 ssl: bool = False, session_id: Optional[str] = None):
        self.client: 'Client' = manager.client
        self.manager: 'NodeManager' = manager
        self._transport = Transport(self, host, port, password, ssl, session_id)

        self.region: str = region
        self.name: str = name or f'{region}-{host}:{port}'
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
    def penalty(self) -> float:
        """ Returns the load-balancing penalty for this node. """
        if not self.available or not self.stats:
            return 9e30

        return self.stats.penalty.total

    async def destroy(self):
        """|coro|

        Destroys the transport and any underlying connections for this node.
        This will also cleanly close the websocket.
        """
        await self._transport.destroy()

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
        return await self._transport._request('GET', 'loadtracks', params={'identifier': query}, to=LoadResult)

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
        return await self._transport._request('GET', 'decodetrack', params={'track': track}, to=AudioTrack)

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
        response = await self._transport._request('POST', 'decodetracks', json=tracks)
        return list(map(AudioTrack, response))

    async def get_routeplanner_status(self) -> Dict[str, Any]:
        """|coro|

        Retrieves the status of the target node's routeplanner.

        Returns
        -------
        Dict[str, Any]
            A dict representing the routeplanner information.
        """
        return await self._transport._request('GET', 'routeplanner/status')

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
            return await self._transport._request('POST', 'routeplanner/free/address', json={'address': address})
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
            return await self._transport._request('POST', 'routeplanner/free/all')
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
        return await self._transport._request('GET', 'info')

    async def get_stats(self) -> Dict[str, Any]:
        """|coro|

        Retrieves statistics about this node.

        Returns
        -------
        Dict[str, Any]
            A raw response containing information about the node.
        """
        return await self._transport._request('GET', 'stats')

    async def get_version(self) -> str:
        """|coro|

        Retrieves the version of this node.

        Returns
        -------
        str
            The version of this Lavalink server.
        """
        return await self._transport._request('GET', 'version', to=str, versioned=False)

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

        return await self._transport._request('GET', f'sessions/{session_id}/players/{guild_id}')

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

        return await self._transport._request('GET', f'sessions/{session_id}/players')

    @overload
    async def update_player(self,
                            guild_id: Union[str, int],
                            encoded_track: Optional[str] = ...,
                            no_replace: bool = ...,
                            position: int = ...,
                            end_time: int = ...,
                            volume: int = ...,
                            paused: bool = ...,
                            filters: Optional[List[Filter]] = ...,
                            voice_state: Dict[str, Any] = ...,
                            user_data: Optional[Dict[str, Any]] = ...,
                            **kwargs) -> Dict[str, Any]:
        ...

    @overload
    async def update_player(self,
                            guild_id: Union[str, int],
                            identifier: str = ...,
                            no_replace: bool = ...,
                            position: int = ...,
                            end_time: int = ...,
                            volume: int = ...,
                            paused: bool = ...,
                            filters: Optional[List[Filter]] = ...,
                            voice_state: Dict[str, Any] = ...,
                            user_data: Dict[str, Any] = ...,
                            **kwargs) -> Dict[str, Any]:
        ...

    @overload
    async def update_player(self,
                            guild_id: Union[str, int],
                            no_replace: bool = ...,
                            position: int = ...,
                            end_time: int = ...,
                            volume: int = ...,
                            paused: bool = ...,
                            filters: Optional[List[Filter]] = ...,
                            voice_state: Dict[str, Any] = ...,
                            user_data: Dict[str, Any] = ...,
                            **kwargs) -> Dict[str, Any]:
        ...

    async def update_player(self,  # pylint: disable=too-many-locals
                            guild_id: Union[str, int],
                            encoded_track: Optional[str] = MISSING,
                            identifier: str = MISSING,
                            no_replace: bool = MISSING,
                            position: int = MISSING,
                            end_time: int = MISSING,
                            volume: int = MISSING,
                            paused: bool = MISSING,
                            filters: Optional[List[Filter]] = MISSING,
                            voice_state: Dict[str, Any] = MISSING,
                            user_data: Dict[str, Any] = MISSING,
                            **kwargs) -> Dict[str, Any]:
        """|coro|

        .. _response object: https://lavalink.dev/api/rest#Player

        Update the state of a player.

        Warning
        -------
        If this function is called directly, rather than through, e.g. a player,
        the internal state is not guaranteed! This means that any attributes accessible through other classes
        may not correspond with those stored in, or provided by the server. Use with caution!

        Parameters
        ----------
        guild_id: Union[str, int]
            The guild ID of the player to update.
        encoded_track: Optional[str]
            The base64-encoded track string to play.
            You may provide ``None`` to stop the player.

            Warning
            -------
            This option is mutually exclusive with ``identifier``. You cannot provide both options.
        identifier: str
            The identifier of the track to play. This can be a track ID or URL. It may not be a
            search query or playlist link. If it yields a search, playlist, or no track, a :class:`RequestError`
            will be raised.

            Warning
            -------
            This option is mutually exclusive with ``encoded_track``. You cannot provide both options.
        no_replace: bool
            Whether to replace the currently playing track (if one exists) with the new track.
            Only takes effect if ``identifier`` or ``encoded_track`` is provided.
            This parameter will only take effect when a track is provided.
        position: int
            The track position in milliseconds. This can be used to seek.
        end_time: int
            The position, in milliseconds, to end the track at.
        volume: int
            The new volume of the player. This must be within the range of 0 to 1000.
        paused: bool
            Whether to pause the player.
        filters: Optional[List[:class:`Filter`]]
            The filters to apply to the player.
            Specify ``None`` or ``[]`` to clear.
        voice_state: Dict[str, Any]
            The new voice state of the player.
        user_data: Dict[str, Any]
            The user data to attach to the track, if one is provided.
            This parameter will only take effect when a track is provided.
        **kwargs: Any
            The kwargs to use when updating the player. You can specify any extra parameters that may be
            used by plugins, which offer extra features not supported out-of-the-box by Lavalink.py.

        Returns
        -------
        Dict[str, Any]
            The raw player update `response object`_.
        """
        session_id = self._transport.session_id

        if not session_id:
            raise ClientError('Cannot update the state of a player without a valid session ID!')

        if encoded_track is not MISSING and identifier is not MISSING:
            raise ValueError('encoded_track and identifier are mutually exclusive options, you may not specify both together.')

        params = {}
        json = kwargs

        if identifier is not MISSING or encoded_track is not MISSING:
            track = {}

            if identifier is not MISSING:
                track['identifier'] = identifier
            elif encoded_track is not MISSING:
                track['encoded'] = encoded_track

            if user_data is not MISSING:
                track['userData'] = user_data

            if no_replace is not MISSING:
                params['noReplace'] = str(no_replace).lower()

            json['track'] = track

        if position is not MISSING:
            if not isinstance(position, (int, float)):
                raise ValueError('position must be an int!')

            json['position'] = position

        if end_time is not MISSING:
            if not isinstance(end_time, int) or end_time <= 0:
                raise ValueError('end_time must be an int, and greater than 0!')

            json['endTime'] = end_time

        if volume is not MISSING:
            if not isinstance(volume, int) or not 0 <= volume <= 1000:
                raise ValueError('volume must be an int, and within the range of 0 to 1000!')

            json['volume'] = volume

        if paused is not MISSING:
            if not isinstance(paused, bool):
                raise ValueError('paused must be a bool!')

            json['paused'] = paused

        if filters is not MISSING:
            if filters is not None:
                if not isinstance(filters, list) or not all(isinstance(f, Filter) for f in filters):
                    raise ValueError('filters must be a list of Filter!')

                serialized = defaultdict(dict)

                for filter_ in filters:
                    filter_obj = serialized['pluginFilters'] if filter_.plugin_filter else serialized
                    filter_obj.update(filter_.serialize())

                json['filters'] = serialized
            else:
                json['filters'] = {}

        if voice_state is not MISSING:
            if not isinstance(voice_state, dict):
                raise ValueError('voice_state must be a dict!')

            json['voice'] = voice_state

        if not json:
            return

        return await self._transport._request('PATCH', f'sessions/{session_id}/players/{guild_id}',
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

        return await self._transport._request('DELETE', f'sessions/{session_id}/players/{guild_id}')

    async def update_session(self, resuming: bool = MISSING, timeout: int = MISSING) -> Dict[str, Any]:
        """|coro|

        Update the session for this node.

        Parameters
        ----------
        resuming: bool
            Whether to enable resuming for this session.
        timeout: int
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

        if resuming is not MISSING:
            if not isinstance(resuming, bool):
                raise ValueError('resuming must be a bool!')

            json['resuming'] = resuming

        if timeout is not MISSING:
            if not isinstance(timeout, int) or 0 >= timeout:
                raise ValueError('timeout must be an int greater than 0!')

            json['timeout'] = timeout

        if not json:
            return

        return await self._transport._request('PATCH', f'sessions/{session_id}', json=json)

    def __repr__(self):
        return f'<Node name={self.name} region={self.region}>'
