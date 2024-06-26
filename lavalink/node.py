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
from asyncio import Task
from collections import defaultdict
from time import time
from typing import (TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar,
                    Union, overload)

from .abc import BasePlayer, Filter
from .common import MISSING
from .errors import AuthenticationError, ClientError, RequestError
from .server import AudioTrack, LoadResult
from .stats import Stats
from .transport import Transport

if TYPE_CHECKING:
    from .client import Client
    from .nodemanager import NodeManager

T = TypeVar('T')


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
    tags: Dict[:class:`str`, Any]
        Additional tags to attach to this node.
    """
    __slots__ = ('client', 'manager', '_transport', 'region', 'name', 'stats', 'tags')

    def __init__(self, manager, host: str, port: int, password: str, region: str, name: Optional[str] = None,
                 ssl: bool = False, session_id: Optional[str] = None, connect: bool = True, tags: Optional[Dict[str, Any]] = None):
        self.client: 'Client' = manager.client
        self.manager: 'NodeManager' = manager
        self._transport = Transport(self, host, port, password, ssl, session_id, connect)

        self.region: str = region
        self.name: str = name or f'{region}-{host}:{port}'
        self.stats: Stats = Stats.empty(self)
        self.tags: Dict[str, Any] = tags or {}

    @property
    def session_id(self) -> Optional[str]:
        """
        The session ID for this node.
        Could be ``None`` if a ready event has not yet been received from the server.
        """
        return self._transport.session_id

    @property
    def available(self) -> bool:
        """
        Returns whether the node has a websocket connection.
        The node could *probably* still be used for HTTP requests even without a WS connection.
        """
        return self._transport.ws_connected

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

    async def get_rest_latency(self) -> float:
        """|coro|

        Measures the REST latency for this node.
        This simply calls :func:`get_version` but measures the time between when the request was made,
        and when a response was received.

        Returns
        -------
        float
            The latency, in milliseconds. ``-1`` if an error occurred during the request (e.g. node is unreachable),
            otherwise, a positive number.
        """
        start = time()

        try:
            await self.get_version()
        except (AuthenticationError, ClientError, RequestError):
            return -1

        return (time() - start) * 1000

    async def connect(self, force: bool = False) -> Optional[Task]:
        """|coro|

        Initiates a WebSocket connection to this node.
        If a connection already exists, and ``force`` is ``False``, this will not do anything.

        Parameters
        ----------
        force: :class:`bool`
            Whether to close any existing WebSocket connections and re-establish a connection to
            the node.

        Returns
        -------
        Optional[:class:`asyncio.Task`]
            The WebSocket connection task, or ``None`` if a WebSocket connection already exists and force
            is ``False``.
        """
        if self._transport.ws_connected:
            if not force:
                return None

            await self._transport.close()

        return self._transport.connect()

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
        return await self.request('GET', 'loadtracks', params={'identifier': query}, to=LoadResult)

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
        return await self.request('GET', 'decodetrack', params={'track': track}, to=AudioTrack)

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
        response = await self.request('POST', 'decodetracks', json=tracks)
        return list(map(AudioTrack, response))  # type: ignore

    async def get_routeplanner_status(self) -> Dict[str, Any]:
        """|coro|

        Retrieves the status of the target node's routeplanner.

        Returns
        -------
        Dict[str, Any]
            A dict representing the routeplanner information.
        """
        return await self.request('GET', 'routeplanner/status')  # type: ignore

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
            return await self.request('POST', 'routeplanner/free/address', json={'address': address})  # type: ignore
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
            return await self.request('POST', 'routeplanner/free/all')  # type: ignore
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
        return await self.request('GET', 'info')  # type: ignore

    async def get_stats(self) -> Dict[str, Any]:
        """|coro|

        Retrieves statistics about this node.

        Returns
        -------
        Dict[str, Any]
            A raw response containing information about the node.
        """
        return await self.request('GET', 'stats')  # type: ignore

    async def get_version(self) -> str:
        """|coro|

        Retrieves the version of this node.

        Returns
        -------
        str
            The version of this Lavalink server.
        """
        return await self.request('GET', 'version', to=str, versioned=False)

    async def get_player(self, guild_id: Union[str, int]) -> Dict[str, Any]:
        """|coro|

        Retrieves a player from the node.
        This returns raw data, to retrieve a player you can interact with, use :func:`PlayerManager.get`.

        Returns
        -------
        Dict[str, Any]
            A raw player object.
        """
        session_id = self.session_id

        if not session_id:
            raise ClientError('Cannot retrieve a player without a valid session ID!')

        return await self.request('GET', f'sessions/{session_id}/players/{guild_id}')  # type: ignore

    async def get_players(self) -> List[Dict[str, Any]]:
        """|coro|

        Retrieves a list of players from the node.
        This returns raw data, to retrieve players you can interact with, use :attr:`players`.

        Returns
        -------
        List[Dict[str, Any]]
            A list of raw player objects.
        """
        session_id = self.session_id

        if not session_id:
            raise ClientError('Cannot retrieve a list of players without a valid session ID!')

        return await self.request('GET', f'sessions/{session_id}/players')  # type: ignore

    @overload
    async def update_player(self,
                            *,
                            guild_id: Union[str, int],
                            encoded_track: Optional[str] = ...,
                            no_replace: bool = ...,
                            position: int = ...,
                            end_time: int = ...,
                            volume: int = ...,
                            paused: bool = ...,
                            filters: Optional[List[Filter]] = ...,
                            voice_state: Dict[str, Any] = ...,
                            user_data: Dict[str, Any] = ...,
                            **kwargs) -> Optional[Dict[str, Any]]:
        ...

    @overload
    async def update_player(self,
                            *,
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
                            **kwargs) -> Optional[Dict[str, Any]]:
        ...

    @overload
    async def update_player(self,
                            *,
                            guild_id: Union[str, int],
                            no_replace: bool = ...,
                            position: int = ...,
                            end_time: int = ...,
                            volume: int = ...,
                            paused: bool = ...,
                            filters: Optional[List[Filter]] = ...,
                            voice_state: Dict[str, Any] = ...,
                            user_data: Dict[str, Any] = ...,
                            **kwargs) -> Optional[Dict[str, Any]]:
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
                            **kwargs) -> Optional[Dict[str, Any]]:
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
        Optional[Dict[str, Any]]
            The raw player update `response object`_, or ``None`` , if a request wasn't made due to an
            empty payload.
        """
        session_id = self.session_id

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
            return None

        return await self.request('PATCH', f'sessions/{session_id}/players/{guild_id}',
                                  params=params, json=json)  # type: ignore

    async def destroy_player(self, guild_id: Union[str, int]) -> bool:
        """|coro|

        Destroys a player on the node.
        It's recommended that you use :func:`PlayerManager.destroy` to destroy a player.

        Returns
        -------
        bool
            Whether the player was destroyed.
        """
        session_id = self.session_id

        if not session_id:
            raise ClientError('Cannot destroy a player without a valid session ID!')

        return await self.request('DELETE', f'sessions/{session_id}/players/{guild_id}')  # type: ignore

    async def update_session(self, resuming: bool = MISSING, timeout: int = MISSING) -> Optional[Dict[str, Any]]:
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
        Optional[Dict[str, Any]]
            A raw response from the node containing the current session configuration, or ``None``
            if a request wasn't made due to an empty payload.
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
            return None

        return await self.request('PATCH', f'sessions/{session_id}', json=json)  # type: ignore

    @overload
    async def request(self, method: str, path: str, *, to: Type[str], trace: bool = ..., versioned: bool = ..., **kwargs) -> str:
        ...

    @overload
    async def request(self, method: str, path: str, *, to: Type[T], trace: bool = ..., versioned: bool = ..., **kwargs) -> T:
        ...

    @overload
    async def request(self, method: str, path: str, *, trace: bool = ..., versioned: bool = ...,  # type: ignore
                      **kwargs) -> Union[Dict[Any, Any], List[Any], bool]:
        ...

    async def request(self,  # type: ignore
                      method: str,
                      path: str,
                      *,
                      to: Optional[Union[Type[T], str]] = None,
                      trace: bool = False,
                      versioned: bool = True,
                      **kwargs) -> Union[T, str, bool, Dict[Any, Any], List[Any]]:
        """|coro|

        .. _HTTP method: https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods

        Makes a HTTP request to this node. Useful for implementing functionality offered by plugins on the server.

        Parameters
        ----------
        method: :class:`str`
            The `HTTP method`_ for this request.
        path: :class:`str`
            The path for this request. E.g. ``sessions/{session_id}/players/{guild_id}``.
        to: Optional[Type[T]]
            The class to deserialize the response into.

            Warning
            -------
            The provided class MUST implement a classmethod called ``from_dict`` that accepts a dict or list object!

            Example:

                .. code:: python

                    @classmethod
                    def from_dict(cls, res: Union[Dict[Any, Any], List[Any]]):
                        return cls(res)
        trace: :class:`bool`
            Whether to enable trace logging for this request. This will return a more detailed error if the request fails,
            but could bloat log files and reduce performance if left enabled.
        versioned: :class:`bool`
            Whether this request should target a versioned route. For the majority of requests, this should be set to ``True``.
            This will prepend the route with the latest API version this client supports, e.g. ``v4/``.
        **kwargs: Any
            Any additional arguments that should be passed to ``aiohttp``. This could be parameters like ``json``, ``params`` etc.

        Raises
        ------
        :class:`AuthenticationError`
            If the provided authorization was invalid.
        :class:`RequestError`
            If the request was unsuccessful.
        :class:`asyncio.TimeoutError`
            If the request times out.
        :class:`aiohttp.ClientError`
            If the remote server disconnects, or a connection fails to establish etc.
        :class:`ClientError`
            A catch-all for anything not covered by the above.

        Returns
        -------
        Union[T, str, bool, Dict[Any, Any], List[Any]]
            - ``T`` or ``str`` if the ``to`` parameter was specified and either value provided.
            - The raw JSON response (``Dict[Any, Any]`` or ``List[Any]``) if ``to`` was not provided.
            - A bool, if the returned status code was ``204``. A value of ``True`` should typically mean the request was successful.
        """
        return await self._transport._request(method, path, to, trace, versioned, **kwargs)

    def __repr__(self):
        return f'<Node name={self.name} region={self.region}>'
