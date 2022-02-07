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
from abc import ABC, abstractmethod
from enum import Enum
from random import randrange
from time import time
from typing import Dict, List, Optional, Union

from .errors import InvalidTrack
from .events import (NodeChangedEvent, QueueEndEvent, TrackEndEvent,
                     TrackExceptionEvent, TrackStartEvent, TrackStuckEvent)
from .filters import Equalizer, Filter


class AudioTrack:
    """
    Represents the AudioTrack sent to Lavalink.

    Parameters
    ----------
    data: :class:`dict`
        The data to initialise an AudioTrack from.
    requester: :class:`any`
        The requester of the track.
    extra: :class:`dict`
        Any extra information to store in this AudioTrack.

    Attributes
    ----------
    track: :class:`str`
        The base64-encoded string representing a Lavalink-readable AudioTrack.
        THIS COULD BE ``None`` IN THE CASE OF :class:`DeferredAudioTrack`.
    identifier: :class:`str`
        The track's id. For example, a youtube track's identifier will look like dQw4w9WgXcQ.
    is_seekable: :class:`bool`
        Whether the track supports seeking.
    author: :class:`str`
        The track's uploader.
    duration: :class:`int`
        The duration of the track, in milliseconds.
    stream: :class:`bool`
        Whether the track is a live-stream.
    title: :class:`str`
        The title of the track.
    uri: :class:`str`
        The full URL of track.
    extra: :class:`dict`
        Any extra properties given to this AudioTrack will be stored here.
    """
    __slots__ = ('track', 'identifier', 'is_seekable', 'author', 'duration', 'stream', 'title', 'uri', 'requester',
                 'extra')

    def __init__(self, data: dict, requester: int, **extra):
        try:
            self._raw = data

            info = data.get('info', data)
            self.track: Optional[str] = data.get('track')
            self.identifier: str = info['identifier']
            self.is_seekable: bool = info['isSeekable']
            self.author: str = info['author']
            self.duration: int = info['length']
            self.stream: bool = info['isStream']
            self.title: str = info['title']
            self.uri: str = info['uri']
            self.requester: int = requester
            self.extra: dict = extra
        except KeyError as ke:
            missing_key, = ke.args
            raise InvalidTrack('Cannot build a track from partial data! (Missing key: {})'.format(missing_key)) from None

    def __getitem__(self, name):
        if name == 'info':
            return self

        return super().__getattribute__(name)

    def __repr__(self):
        return '<AudioTrack title={0.title} identifier={0.identifier}>'.format(self)


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
    __slots__ = ('track', 'identifier', 'is_seekable', 'author', 'duration', 'stream', 'title', 'uri', 'requester',
                 'extra')

    @abstractmethod
    async def load(self, client):
        """
        Retrieves a base64 string that's playable by Lavalink.
        For example, you can use this method to search Lavalink for an identical track from other sources,
        which you can then use the base64 string of to play the track on Lavalink.

        Parameters
        ----------
        client: :class:`Client`
            This will be an instance of the Lavalink client 'linked' to this track.

        Returns
        -------
        :class:`str`
            A Lavalink-compatible base64 string containing encoded track metadata.
        """
        raise NotImplementedError


class LoadType(Enum):
    TRACK = 'TRACK_LOADED'
    PLAYLIST = 'PLAYLIST_LOADED'
    SEARCH = 'SEARCH_RESULT'
    NO_MATCHES = 'NO_MATCHES'
    LOAD_FAILED = 'LOAD_FAILED'

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value  # pylint: disable=comparison-with-callable

        if isinstance(other, str):
            return self.value == other  # pylint: disable=comparison-with-callable

        raise NotImplementedError

    @classmethod
    def from_str(cls, other: str):
        try:
            return cls[other.upper()]
        except KeyError:
            try:
                return cls(other.upper())
            except ValueError as ve:
                raise ValueError('{} is not a valid LoadType enum!'.format(other)) from ve


class PlaylistInfo:
    """
    Attributes
    ----------
    name: :class:`str`
        The name of the playlist.
    selected_track: :class:`int`
        The index of the selected/highlighted track.
        This will be -1 if there is no selected track.
    """
    def __init__(self, name: str, selected_track: int = -1):
        self.name: str = name
        self.selected_track: int = selected_track

    def __getitem__(self, k):  # Exists only for compatibility, don't blame me
        if k == 'selectedTrack':
            k = 'selected_track'
        return self.__getattribute__(k)

    @classmethod
    def from_dict(cls, mapping: dict):
        return cls(mapping.get('name'), mapping.get('selectedTrack', -1))

    @classmethod
    def none(cls):
        return cls('', -1)


class LoadResult:
    """
    Attributes
    ----------
    load_type: :class:`LoadType`
        The load type of this result.
    tracks: List[Union[:class:`AudioTrack`, :class:`DeferredAudioTrack`]]
        The tracks in this result.
    playlist_info: :class:`PlaylistInfo`
        The playlist metadata for this result.
        The :class:`PlaylistInfo` could contain empty/false data if the :class:`LoadType`
        is not :enum:`LoadType.PLAYLIST`.
    """
    def __init__(self, load_type: LoadType, tracks: List[Union[AudioTrack, DeferredAudioTrack]],
                 playlist_info: Optional[PlaylistInfo] = PlaylistInfo.none()):
        self.load_type: LoadType = load_type
        self.playlist_info: PlaylistInfo = playlist_info
        self.tracks: List[Union[AudioTrack, DeferredAudioTrack]] = tracks

    def __getitem__(self, k):  # Exists only for compatibility, don't blame me
        if k == 'loadType':
            k = 'load_type'
        elif k == 'playlistInfo':
            k = 'playlist_info'

        return self.__getattribute__(k)

    @classmethod
    def from_dict(cls, mapping: dict):
        load_type = LoadType.from_str(mapping.get('loadType'))
        playlist_info = PlaylistInfo.from_dict(mapping.get('playlistInfo'))
        tracks = [AudioTrack(track, 0) for track in mapping.get('tracks')]
        return cls(load_type, tracks, playlist_info)


class Source(ABC):
    def __init__(self, name: str):
        self.name: str = name

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.name == other.name

        raise NotImplementedError

    def __hash__(self):
        return hash(self.name)

    @abstractmethod
    async def load_item(self, client, query: str) -> Optional[LoadResult]:
        """
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
            A LoadResult, or None if there were no matches for the provided query.
        """
        raise NotImplementedError


class BasePlayer(ABC):
    """
    Represents the BasePlayer all players must be inherited from.

    Attributes
    ----------
    guild_id: :class:`int`
        The guild id of the player.
    node: :class:`Node`
        The node that the player is connected to.
    channel_id: Optional[:class:`int`]
        The ID of the voice channel the player is connected to.
        This could be None if the player isn't connected.
    """
    def __init__(self, guild_id, node):
        self.guild_id = guild_id
        self._internal_id = str(guild_id)
        self.node = node
        self._original_node = None  # This is used internally for failover.
        self._voice_state = {}
        self.channel_id: Optional[int] = None

    @abstractmethod
    async def _handle_event(self, event):
        raise NotImplementedError

    @abstractmethod
    async def _update_state(self, state: dict):
        raise NotImplementedError

    def cleanup(self):
        pass

    async def _voice_server_update(self, data):
        self._voice_state.update({
            'event': data
        })

        await self._dispatch_voice_update()

    async def _voice_state_update(self, data):
        self._voice_state.update({
            'sessionId': data['session_id']
        })

        raw_channel_id = data['channel_id']
        self.channel_id = int(raw_channel_id) if raw_channel_id else None

        if not self.channel_id:  # We're disconnecting
            self._voice_state.clear()
            return

        await self._dispatch_voice_update()

    async def _dispatch_voice_update(self):
        if {'sessionId', 'event'} == self._voice_state.keys():
            await self.node._send(op='voiceUpdate', guildId=self._internal_id, **self._voice_state)

    @abstractmethod
    async def change_node(self, node):
        raise NotImplementedError


class DefaultPlayer(BasePlayer):
    """
    The player that Lavalink.py defaults to use.

    Attributes
    ----------
    guild_id: :class:`int`
        The guild id of the player.
    node: :class:`Node`
        The node that the player is connected to.
    paused: :class:`bool`
        Whether or not a player is paused.
    position_timestamp: :class:`int`
        Returns the track's elapsed playback time as an epoch timestamp.
    volume: :class:`int`
        The volume at which the player is playing at.
    shuffle: :class:`bool`
        Whether or not to mix the queue up in a random playing order.
    repeat: :class:`bool`
        Whether or not to continuously to play a track.
    filters: :class:`dict`
        A mapping of filter names, to their respective :class:`Filter` instance.
    queue: :class:`list`
        The order of which tracks are played.
    current: :class:`AudioTrack`
        The track that is playing currently.
    """
    def __init__(self, guild_id, node):
        super().__init__(guild_id, node)

        self._user_data = {}

        self.paused = False
        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.volume = 100
        self.shuffle = False
        self.repeat = False
        # self.equalizer = [0.0 for x in range(15)]  # 0-14, -0.25 - 1.0
        self.filters: Dict[str, Filter] = {}

        self.queue = []
        self.current = None

    @property
    def is_playing(self) -> bool:
        """ Returns the player's track state. """
        return self.is_connected and self.current is not None

    @property
    def is_connected(self) -> bool:
        """ Returns whether the player is connected to a voicechannel or not. """
        return self.channel_id is not None

    @property
    def position(self) -> float:
        """ Returns the track's elapsed playback time in milliseconds, adjusted for Lavalink stat interval. """
        if not self.is_playing:
            return 0

        if self.paused:
            return min(self._last_position, self.current.duration)

        difference = time() * 1000 - self._last_update
        return min(self._last_position + difference, self.current.duration)

    def store(self, key: object, value: object):
        """
        Stores custom user data.

        Parameters
        ----------
        key: :class:`object`
            The key of the object to store.
        value: :class:`object`
            The object to associate with the key.
        """
        self._user_data.update({key: value})

    def fetch(self, key: object, default=None):
        """
        Retrieves the related value from the stored user data.

        Parameters
        ----------
        key: :class:`object`
            The key to fetch.
        default: Optional[:class:`any`]
            The object that should be returned if the key doesn't exist. Defaults to `None`.

        Returns
        -------
        :class:`any`
        """
        return self._user_data.get(key, default)

    def delete(self, key: object):
        """
        Removes an item from the the stored user data.

        Parameters
        ----------
        key: :class:`object`
            The key to delete.
        """
        try:
            del self._user_data[key]
        except KeyError:
            pass

    def add(self, track: Union[AudioTrack, DeferredAudioTrack, Dict], requester: int = 0, index: int = None):
        """
        Adds a track to the queue.

        Parameters
        ----------
        track: Union[:class:`AudioTrack`, :class:`DeferredAudioTrack`, :class:`dict`]
            The track to add. Accepts either an AudioTrack or
            a dict representing a track returned from Lavalink.
        requester: :class:`int`
            The ID of the user who requested the track.
        index: Optional[:class:`int`]
            The index at which to add the track.
            If index is left unspecified, the default behaviour is to append the track. Defaults to `None`.
        """
        at = track

        if isinstance(track, dict):
            at = AudioTrack(track, requester)

        if requester != 0:
            at.requester = requester

        if index is None:
            self.queue.append(at)
        else:
            self.queue.insert(index, at)

    async def play(self, track: Union[AudioTrack, DeferredAudioTrack, Dict] = None, start_time: int = 0, end_time: int = 0,
                   no_replace: bool = False):
        """
        Plays the given track.

        Parameters
        ----------
        track: Optional[Union[:class:`DeferredAudioTrack`, :class:`AudioTrack`, :class:`dict`]]
            The track to play. If left unspecified, this will default
            to the first track in the queue. Defaults to `None` so plays the next
            song in queue. Accepts either an AudioTrack or a dict representing a track
            returned from Lavalink.
        start_time: Optional[:class:`int`]
            Setting that determines the number of milliseconds to offset the track by.
            If left unspecified, it will start the track at its beginning. Defaults to `0`,
            which is the normal start time.
        end_time: Optional[:class:`int`]
            Settings that determines the number of milliseconds the track will stop playing.
            By default track plays until it ends as per encoded data. Defaults to `0`, which is
            the normal end time.
        no_replace: Optional[:class:`bool`]
            If set to true, operation will be ignored if a track is already playing or paused.
            Defaults to `False`
        """
        if track is not None and isinstance(track, dict):
            track = AudioTrack(track, 0)

        if self.repeat and self.current:
            self.queue.append(self.current)

        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.paused = False

        if not track:
            if not self.queue:
                await self.stop()  # Also sets current to None.
                await self.node._dispatch_event(QueueEndEvent(self))
                return

            pop_at = randrange(len(self.queue)) if self.shuffle else 0
            track = self.queue.pop(pop_at)

        options = {}

        if start_time is not None:
            if not isinstance(start_time, int) or not 0 <= start_time <= track.duration:
                raise ValueError('start_time must be an int with a value equal to, or greater than 0, and less than the track duration')
            options['startTime'] = start_time

        if end_time is not None:
            if not isinstance(end_time, int) or not 0 <= end_time <= track.duration:
                raise ValueError('end_time must be an int with a value equal to, or greater than 0, and less than the track duration')
            options['endTime'] = end_time

        if no_replace is None:
            no_replace = False
        if not isinstance(no_replace, bool):
            raise TypeError('no_replace must be a bool')

        options['noReplace'] = no_replace
        self.current = track
        playable_track = track.track

        if isinstance(track, DeferredAudioTrack) and playable_track is None:
            playable_track = await track.load(self.node._manager._lavalink)

        await self.node._send(op='play', guildId=self._internal_id, track=playable_track, **options)
        await self.node._dispatch_event(TrackStartEvent(self, track))

    async def stop(self):
        """ Stops the player. """
        await self.node._send(op='stop', guildId=self._internal_id)
        self.current = None

    async def skip(self):
        """ Plays the next track in the queue, if any. """
        await self.play()

    def set_repeat(self, repeat: bool):
        """
        Sets whether tracks should be repeated.

        This only works as a "queue loop". For single-track looping, you should
        utilise the :class:`TrackEndEvent` event to feed the track back into
        :func:`play`.

        Also known as ``loop``.

        Parameters
        ----------
        repeat: :class:`bool`
            Whether to repeat the player or not.
        """
        self.repeat = repeat

    def set_shuffle(self, shuffle: bool):
        """
        Sets the player's shuffle state.
        Parameters
        ----------
        shuffle: :class:`bool`
            Whether to shuffle the player or not.
        """
        self.shuffle = shuffle

    async def set_pause(self, pause: bool):
        """
        Sets the player's paused state.

        Parameters
        ----------
        pause: :class:`bool`
            Whether to pause the player or not.
        """
        await self.node._send(op='pause', guildId=self._internal_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        """
        Sets the player's volume

        Note
        ----
        A limit of 1000 is imposed by Lavalink.

        Parameters
        ----------
        vol: :class:`int`
            The new volume level.
        """
        await self.node._send(op='volume', guildId=self._internal_id, volume=self.volume)
        self.volume = max(min(vol, 1000), 0)

    async def seek(self, position: int):
        """
        Seeks to a given position in the track.

        Parameters
        ----------
        position: :class:`int`
            The new position to seek to in milliseconds.
        """
        await self.node._send(op='seek', guildId=self._internal_id, position=position)

    async def set_filter(self, _filter: Filter):
        """
        Applies the corresponding filter within Lavalink.
        This will overwrite the filter if it's already applied.

        Example
        -------
        .. code:: python

            equalizer = Equalizer()
            equalizer.update(bands=[(0, 0.2), (1, 0.3), (2, 0.17)])
            player.set_filter(equalizer)
        """
        if not isinstance(_filter, Filter):
            raise TypeError('Expected object of type Filter, not ' + type(_filter).__name__)

        filter_name = type(_filter).__name__.lower()
        self.filters[filter_name] = _filter
        await self._apply_filters()

    async def get_filter(self, _filter: Union[Filter, str]):
        """
        Returns the corresponding filter, if it's enabled.

        Example
        -------
        .. code:: python

            from lavalink.filters import Timescale
            timescale = player.get_filter(Timescale)
            # or
            timescale = player.get_filter('timescale')

        Returns
        -------
        Optional[:class:`Filter`]
        """
        if isinstance(_filter, str):
            filter_name = _filter
        elif isinstance(_filter, Filter):  # User passed an instance of.
            filter_name = type(_filter).__name__
        else:
            filter_name = _filter.__name__

        return self.filters.get(filter_name.lower(), None)

    async def remove_filter(self, _filter: Union[Filter, str]):
        """
        Removes a filter from the player, undoing any effects applied to the audio.

        Example
        -------
        .. code:: python

            player.remove_filter(Timescale)
            # or
            player.remove_filter('timescale')
        """
        if isinstance(_filter, str):
            filter_name = _filter
        elif isinstance(_filter, Filter):  # User passed an instance of.
            filter_name = type(_filter).__name__
        else:
            filter_name = _filter.__name__

        fn_lowered = filter_name.lower()

        if fn_lowered in self.filters:
            self.filters.pop(fn_lowered)
            await self._apply_filters()

    async def set_gain(self, band: int, gain: float = 0.0):
        """
        Sets the equalizer band gain to the given amount.

        .. deprecated:: 4.0.0
            Use :func:`set_filter` to apply the :class:`Equalizer` filter instead.

        Parameters
        ----------
        band: :class:`int`
            Band number (0-14).
        gain: Optional[:class:`float`]
            A float representing gain of a band (-0.25 to 1.00). Defaults to 0.0.
        """
        await self.set_gains((band, gain))

    async def set_gains(self, *bands):
        """
        Modifies the player's equalizer settings.

        .. deprecated:: 4.0.0
            Use :func:`set_filter` to apply the :class:`Equalizer` filter instead.

        Parameters
        ----------
        gain_list: :class:`any`
            A list of tuples denoting (`band`, `gain`).
        """
        equalizer = Equalizer()
        equalizer.update(bands=bands)
        await self.set_filter(equalizer)

    async def reset_equalizer(self):
        """
        Resets equalizer to default values.

        .. deprecated:: 4.0.0
            Use :func:`remove_filter` to remove the :class:`Equalizer` filter instead.
        """
        await self.remove_filter(Equalizer)

    async def _apply_filters(self):
        payload = {}

        for _filter in self.filters.values():
            payload.update(_filter.serialize())

        await self.node._send(op='filters', guildId=self._internal_id, **payload)

    async def _handle_event(self, event):
        """
        Handles the given event as necessary.

        Parameters
        ----------
        event: :class:`Event`
            The event that will be handled.
        """
        if isinstance(event, (TrackStuckEvent, TrackExceptionEvent)) or \
                isinstance(event, TrackEndEvent) and event.reason == 'FINISHED':
            await self.play()

    async def _update_state(self, state: dict):
        """
        Updates the position of the player.

        Parameters
        ----------
        state: :class:`dict`
            The state that is given to update.
        """
        self._last_update = time() * 1000
        self._last_position = state.get('position', 0)
        self.position_timestamp = state.get('time', 0)

    async def change_node(self, node):
        """
        Changes the player's node

        Parameters
        ----------
        node: :class:`Node`
            The node the player is changed to.
        """
        if self.node.available:
            await self.node._send(op='destroy', guildId=self._internal_id)

        old_node = self.node
        self.node = node

        if self._voice_state:
            await self._dispatch_voice_update()

        if self.current:
            playable_track = self.current.track

            if isinstance(self.current, DeferredAudioTrack) and playable_track is None:
                playable_track = await self.current.load(self.node._manager._lavalink)

            await self.node._send(op='play', guildId=self._internal_id, track=playable_track, startTime=self.position)
            self._last_update = time() * 1000

            if self.paused:
                await self.node._send(op='pause', guildId=self._internal_id, pause=self.paused)

        if self.volume != 100:
            await self.node._send(op='volume', guildId=self._internal_id, volume=self.volume)

        if self.filters:
            await self._apply_filters()

        await self.node._dispatch_event(NodeChangedEvent(self, old_node, node))
