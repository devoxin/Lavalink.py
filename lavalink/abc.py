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
import logging
from abc import ABC, abstractmethod
from typing import (TYPE_CHECKING, Any, Dict, Final, Generic, List, Optional,
                    TypeVar, Union, cast)

from .common import MISSING, VoiceServerUpdateData, VoiceStateUpdateData
from .errors import InvalidTrack, LoadError
from .events import Event, TrackLoadFailedEvent
from .server import AudioTrack, RawPlayer, RawPlayerState

if TYPE_CHECKING:
    from .client import Client
    from .node import Node
    from .server import LoadResult

_log = logging.getLogger(__name__)

FilterValueT = TypeVar('FilterValueT', Dict[str, Any], List[float], List[int], float)


class BasePlayer(ABC):
    """
    Represents the BasePlayer all players must be inherited from.

    Attributes
    ----------
    client: :class:`Client`
        The Lavalink client instance.
    guild_id: :class:`int`
        The guild id of the player.
    node: :class:`Node`
        The node that the player is connected to.
    channel_id: Optional[:class:`int`]
        The ID of the voice channel the player is connected to.
        This could be ``None`` if the player isn't connected.
    current: Optional[:class:`AudioTrack`]
        The currently playing track.
    """
    __slots__ = ('client', 'guild_id', 'node', 'channel_id', 'current', '_next', '_internal_id',
                 '_original_node', '_voice_state')

    def __init__(self, guild_id: int, node: 'Node'):
        self.client: Final['Client'] = node.manager.client
        self.guild_id: Final[int] = guild_id
        self.node: 'Node' = node
        self.channel_id: Optional[int] = None
        self.current: Optional[AudioTrack] = None

        self._next: Optional[AudioTrack] = None
        self._internal_id: Final[str] = str(guild_id)
        self._original_node: Optional['Node'] = None  # This is used internally for failover.
        self._voice_state = {}

    @abstractmethod
    async def handle_event(self, event: Event):
        """|coro|

        Handles an :class:`Event` received directly from the websocket.

        Parameters
        ----------
        event: :class:`Event`
            The event that will be handled.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_state(self, state: RawPlayerState):
        """|coro|

        .. _state object: https://lavalink.dev/api/websocket#player-state

        Updates this player's state with the `state object`_ received from the server.

        Parameters
        ----------
        state: Dict[:class:`str`, Any]
            The player state.
        """
        raise NotImplementedError

    async def play_track(self,
                         track: Union[AudioTrack, 'DeferredAudioTrack'],
                         start_time: int = MISSING,
                         end_time: int = MISSING,
                         no_replace: bool = MISSING,
                         volume: int = MISSING,
                         pause: bool = MISSING,
                         **kwargs) -> Optional[RawPlayer]:
        """|coro|

        .. _player object: https://lavalink.dev/api/rest.html#Player

        Plays the given track.

        Warning
        -------
        Multiple calls to this method within a short timeframe could cause issues with the player's
        internal state, which can cause errors when processing a :class:`TrackStartEvent`.

        Parameters
        ----------
        track: Union[:class:`AudioTrack`, :class:`DeferredAudioTrack`]
            The track to play.
        start_time: :class:`int`
            The number of milliseconds to offset the track by.
            If left unspecified or ``None`` is provided, the track will start from the beginning.
        end_time: :class:`int`
            The position at which the track should stop playing.
            This is an absolute position, so if you want the track to stop at 1 minute, you would pass 60000.
            The default behaviour is to play until no more data is received from the remote server.
            If left unspecified or ``None`` is provided, the default behaviour is exhibited.
        no_replace: :class:`bool`
            If set to true, operation will be ignored if a track is already playing or paused.
            The default behaviour is to always replace.
            If left unspecified or ``None`` is provided, the default behaviour is exhibited.
        volume: :class:`int`
            The initial volume to set. This is useful for changing the volume between tracks etc.
            If left unspecified or ``None`` is provided, the volume will remain at its current setting.
        pause: :class:`bool`
            Whether to immediately pause the track after loading it.
            The default behaviour is to never pause.
            If left unspecified or ``None`` is provided, the default behaviour is exhibited.
        **kwargs: Any
            The kwargs to use when playing. You can specify any extra parameters that may be
            used by plugins, which offer extra features not supported out-of-the-box by Lavalink.py.

        Returns
        -------
        Optional[:class:`RawPlayer`]
            The updated `player object`_, or ``None`` if a request wasn't made due to an empty payload.
        """
        if track is MISSING or not isinstance(track, AudioTrack):
            raise ValueError('track must be an instance of an AudioTrack!')

        options = kwargs

        if start_time is not MISSING:
            if not isinstance(start_time, int) or 0 > start_time:
                raise ValueError('start_time must be an int with a value equal to, or greater than 0')

            options['position'] = start_time

        if end_time is not MISSING:
            if not isinstance(end_time, int) or 1 > end_time:
                raise ValueError('end_time must be an int with a value equal to, or greater than 1')

            options['end_time'] = end_time

        if no_replace is not MISSING:
            if not isinstance(no_replace, bool):
                raise TypeError('no_replace must be a bool')

            options['no_replace'] = no_replace

        if volume is not MISSING:
            if not isinstance(volume, int):
                raise TypeError('volume must be an int')

            options['volume'] = max(min(volume, 1000), 0)

        if pause is not MISSING:
            if not isinstance(pause, bool):
                raise TypeError('pause must be a bool')

            options['paused'] = pause

        playable_track = track.track

        if playable_track is None:
            if not isinstance(track, DeferredAudioTrack):
                raise InvalidTrack('Cannot play the AudioTrack as \'track\' is None, and it is not a DeferredAudioTrack!')

            try:
                playable_track = await track.load(self.client)
            except LoadError as load_error:
                self.client._dispatch_event(TrackLoadFailedEvent(self, track, load_error))
                return

        if playable_track is None:  # This should only fire when a DeferredAudioTrack fails to yield a base64 track string.
            self.client._dispatch_event(TrackLoadFailedEvent(self, track, None))  # type: ignore
            return

        self._next = track
        response = await self.node.update_player(guild_id=self._internal_id, encoded_track=playable_track, **options)
        return cast(RawPlayer, response)

    def cleanup(self):
        pass

    async def destroy(self):
        """|coro|

        Destroys the current player instance.

        Shortcut for :func:`PlayerManager.destroy`.
        """
        await self.client.player_manager.destroy(self.guild_id)

    async def _voice_server_update(self, data: VoiceServerUpdateData):
        self._voice_state.update(endpoint=data['endpoint'], token=data['token'])

        if 'sessionId' not in self._voice_state:
            # We should've received session_id from a VOICE_STATE_UPDATE before receiving a VOICE_SERVER_UPDATE.
            _log.warning('[Player:%s] Missing sessionId, is the client User ID correct?', self.guild_id)

        await self._dispatch_voice_update()

    async def _voice_state_update(self, data: VoiceStateUpdateData):
        raw_channel_id = data['channel_id']
        self.channel_id = int(raw_channel_id) if raw_channel_id else None

        if not self.channel_id:  # We're disconnecting
            self._voice_state.clear()
            return

        if data['session_id'] != self._voice_state.get('sessionId'):
            self._voice_state.update(sessionId=data['session_id'])

            await self._dispatch_voice_update()

    async def _dispatch_voice_update(self):
        if {'sessionId', 'endpoint', 'token'} == self._voice_state.keys():
            await self.node.update_player(guild_id=self._internal_id, voice_state=self._voice_state)  # type: ignore

    @abstractmethod
    async def node_unavailable(self):
        """|coro|

        Called when a player's node becomes unavailable.
        Useful for changing player state before it's moved to another node.
        """
        raise NotImplementedError

    @abstractmethod
    async def change_node(self, node: 'Node'):
        """|coro|

        Called when a node change is requested for the current player instance.

        Parameters
        ----------
        node: :class:`Node`
            The new node to switch to.
        """
        raise NotImplementedError


class DeferredAudioTrack(ABC, AudioTrack):
    """
    Similar to an :class:`AudioTrack`, however this track only stores metadata up until it's
    played, at which time :func:`load` is called to retrieve a base64 string which is then used for playing.

    Note
    ----
    For implementation: The ``track`` field need not be populated as this is done later via
    the :func:`load` method. You can optionally set ``self.track`` to the result of :func:`load`
    during implementation, as a means of caching the base64 string to avoid fetching it again later.
    This should serve the purpose of speeding up subsequent play calls in the event of repeat being enabled,
    for example.
    """
    __slots__ = ()

    @abstractmethod
    async def load(self, client: 'Client') -> Optional[str]:
        """|coro|

        Retrieves a base64 string that's playable by Lavalink.
        For example, you can use this method to search Lavalink for an identical track from other sources,
        which you can then use the base64 string of to play the track on Lavalink.

        Parameters
        ----------
        client: :class:`Client`
            This will be an instance of the Lavalink client 'linked' to this track.

        Returns
        -------
        Optional[:class:`str`]
            A Lavalink-compatible base64-encoded string containing track metadata.
            If a track string cannot be returned, you may return ``None`` or throw a :class:`LoadError`.
        """
        raise NotImplementedError


class Source(ABC):
    __slots__ = ('name',)

    def __init__(self, name: str):
        self.name: str = name

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.name == other.name

        return False

    def __hash__(self):
        return hash(self.name)

    @abstractmethod
    async def load_item(self, client: 'Client', query: str) -> Optional['LoadResult']:
        """|coro|

        Loads a track with the given query.

        Parameters
        ----------
        client: :class:`Client`
            The Lavalink client. This could be useful for performing a Lavalink search
            for an identical track from other sources, if needed.
        query: :class:`str`
            The search query that was provided.

        Returns
        -------
        Optional[:class:`LoadResult`]
            A LoadResult, or ``None`` if there were no matches for the provided query.
        """
        raise NotImplementedError

    def __repr__(self):
        return f'<Source name={self.name}>'


class Filter(ABC, Generic[FilterValueT]):
    """
    A class representing a Lavalink audio filter.

    Parameters
    ----------
    values: Union[Dict[str, Any], List[Union[float, int]], float]
        The values for this filter.
    plugin_filter: :class:`bool`
        Whether this filter is part of a Lavalink plugin. Typically, this will be ``True``
        when creating your own filters.

    Attributes
    ----------
    values: Union[Dict[str, Any], List[Union[float, int]], float]
        The values for this filter.
    plugin_filter: :class:`bool`
        Whether this filter is part of a Lavalink plugin.
    """
    __slots__ = ('values', 'plugin_filter')

    def __init__(self, values: FilterValueT, plugin_filter: bool = False):
        self.values: FilterValueT = values
        self.plugin_filter: Final[bool] = plugin_filter

    @abstractmethod
    def update(self, **kwargs):
        """ Updates the internal values to match those provided. """
        raise NotImplementedError

    @abstractmethod
    def serialize(self) -> Dict[str, FilterValueT]:
        """
        Transforms the internal values into a dict matching the structure Lavalink expects.

        Example:

            .. code:: python

                return {"yourCustomFilter": {"gain": 5}}
        """
        raise NotImplementedError
