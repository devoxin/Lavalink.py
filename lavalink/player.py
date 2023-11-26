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
from random import randrange
from time import time
from typing import TYPE_CHECKING, Dict, List, Optional, Type, TypeVar, Union  # Literal

from .abc import BasePlayer, DeferredAudioTrack
from .errors import InvalidTrack, LoadError, PlayerErrorEvent, RequestError
from .events import (NodeChangedEvent, QueueEndEvent, TrackEndEvent,
                     TrackLoadFailedEvent, TrackStartEvent, TrackStuckEvent)
from .filters import Filter
from .server import AudioTrack

if TYPE_CHECKING:
    from .node import Node

_log = logging.getLogger(__name__)

FilterT = TypeVar('FilterT', bound=Filter)


class DefaultPlayer(BasePlayer):
    """
    The player that Lavalink.py uses by default.

    This should be sufficient for most use-cases.

    Attributes
    ----------
    LOOP_NONE: :class:`int`
        Class attribute. Disables looping entirely.
    LOOP_SINGLE: :class:`int`
        Class attribute. Enables looping for a single (usually currently playing) track only.
    LOOP_QUEUE: :class:`int`
        Class attribute. Enables looping for the entire queue. When a track finishes playing, it'll be added to the end of the queue.

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
    loop: Literal[0, 1, 2]
        Whether loop is enabled, and the type of looping.
        This is an integer as loop supports multiple states.

        0 = Loop off.

        1 = Loop track.

        2 = Loop queue.

        Example
        -------
        .. code:: python

            if player.loop == player.LOOP_NONE:
                await ctx.send('Not looping.')
            elif player.loop == player.LOOP_SINGLE:
                await ctx.send(f'{player.current.title} is looping.')
            elif player.loop == player.LOOP_QUEUE:
                await ctx.send('This queue never ends!')
    filters: Dict[:class:`str`, :class:`Filter`]
        A mapping of str to :class:`Filter`, representing currently active filters.
    queue: List[:class:`AudioTrack`]
        A list of AudioTracks to play.
    current: Optional[:class:`AudioTrack`]
        The track that is playing currently, if any.
    """
    LOOP_NONE: int = 0
    LOOP_SINGLE: int = 1
    LOOP_QUEUE: int = 2

    def __init__(self, guild_id: int, node: 'Node'):
        super().__init__(guild_id, node)

        self._user_data = {}

        self.paused: bool = False
        self._internal_pause: bool = False  # Toggled when player's node becomes unavailable, primarily used for track position tracking.
        self._last_update: int = 0
        self._last_position: int = 0
        self.position_timestamp: int = 0
        self.volume: int = 100
        self.shuffle: bool = False
        self.loop: int = 0  # 0 = off, 1 = single track, 2 = queue
        self.filters: Dict[str, Filter] = {}

        self.queue: List[AudioTrack] = []
        self.current: Optional[AudioTrack] = None

    @property
    def is_playing(self) -> bool:
        """ Returns the player's track state. """
        return self.is_connected and self.current is not None

    @property
    def is_connected(self) -> bool:
        """ Returns whether the player is connected to a voicechannel or not. """
        return self.channel_id is not None

    @property
    def position(self) -> int:
        """ Returns the track's elapsed playback time in milliseconds, adjusted for Lavalink stat interval. """
        if not self.is_playing:
            return 0

        if self.paused or self._internal_pause:
            return min(self._last_position, self.current.duration)

        difference = int(time() * 1000) - self._last_update
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
            The object that should be returned if the key doesn't exist. Defaults to ``None``.

        Returns
        -------
        Optional[:class:`any`]
        """
        return self._user_data.get(key, default)

    def delete(self, key: object):
        """
        Removes an item from the the stored user data.

        Parameters
        ----------
        key: :class:`object`
            The key to delete.

        Raises
        ------
        :class:`KeyError`
            If the key doesn't exist.
        """
        try:
            del self._user_data[key]
        except KeyError:
            pass

    def add(self, track: Union[AudioTrack, 'DeferredAudioTrack', Dict[str, Union[Optional[str], bool, int]]],
            requester: int = 0, index: int = None):
        """
        Adds a track to the queue.

        Parameters
        ----------
        track: Union[:class:`AudioTrack`, :class:`DeferredAudioTrack`, Dict[str, Union[Optional[str], bool, int]]]
            The track to add. Accepts either an AudioTrack or
            a dict representing a track returned from Lavalink.
        requester: :class:`int`
            The ID of the user who requested the track.
        index: Optional[:class:`int`]
            The index at which to add the track.
            If index is left unspecified, the default behaviour is to append the track. Defaults to ``None``.
        """
        at = AudioTrack(track, requester) if isinstance(track, dict) else track

        if requester != 0:
            at.requester = requester

        if index is None:
            self.queue.append(at)
        else:
            self.queue.insert(index, at)

    async def play(self, track: Optional[Union[AudioTrack, 'DeferredAudioTrack', Dict[str, Union[Optional[str], bool, int]]]] = None,
                   start_time: Optional[int] = 0, end_time: Optional[int] = None, no_replace: Optional[bool] = False,
                   volume: Optional[int] = None, pause: Optional[bool] = False, **kwargs):
        """|coro|

        Plays the given track.

        This method differs from :meth:`BasePlayer.play_track` in that it contains additional logic
        to handle certain attributes, such as ``loop``, ``shuffle``, and loading a base64 string from :class:`DeferredAudioTrack`.

        :meth:`BasePlayer.play_track` is a no-frills, raw function which will unconditionally tell the node to play exactly whatever
        it is passed.

        Parameters
        ----------
        track: Optional[Union[:class:`DeferredAudioTrack`, :class:`AudioTrack`, Dict[str, Union[Optional[str], bool, int]]]]
            The track to play. If left unspecified, this will default
            to the first track in the queue. Defaults to ``None`` so plays the next
            song in queue. Accepts either an AudioTrack or a dict representing a track
            returned from Lavalink.
        start_time: Optional[:class:`int`]
            The number of milliseconds to offset the track by.
            If left unspecified or ``None`` is provided, the track will start from the beginning.
        end_time: Optional[:class:`int`]
            The position at which the track should stop playing.
            This is an absolute position, so if you want the track to stop at 1 minute, you would pass 60000.
            The default behaviour is to play until no more data is received from the remote server.
            If left unspecified or ``None`` is provided, the default behaviour is exhibited.
        no_replace: Optional[:class:`bool`]
            If set to true, operation will be ignored if a track is already playing or paused.
            The default behaviour is to always replace.
            If left unspecified or None is provided, the default behaviour is exhibited.
        volume: Optional[:class:`int`]
            The initial volume to set. This is useful for changing the volume between tracks etc.
            If left unspecified or ``None`` is provided, the volume will remain at its current setting.
        pause: Optional[:class:`bool`]
            Whether to immediately pause the track after loading it.
            The default behaviour is to never pause.
            If left unspecified or ``None`` is provided, the default behaviour is exhibited.
        **kwargs: :class:`any`
            The kwargs to use when playing. You can specify any extra parameters that may be
            used by plugins, which offer extra features not supported out-of-the-box by Lavalink.py.

        Raises
        ------
        :class:`ValueError`
            If invalid values were provided for ``start_time`` or ``end_time``.
        :class:`TypeError`
            If wrong types were provided for ``no_replace``, ``volume`` or ``pause``.
        """
        if no_replace and self.is_playing:
            return

        if track is not None and isinstance(track, dict):
            track = AudioTrack(track, 0)

        if self.loop > 0 and self.current:
            if self.loop == 1:
                if track is not None:
                    self.queue.insert(0, self.current)
                else:
                    track = self.current
            elif self.loop == 2:
                self.queue.append(self.current)

        self._last_position = 0
        self.position_timestamp = 0
        self.paused = pause

        if not track:
            if not self.queue:
                await self.stop()  # Also sets current to None.
                await self.client._dispatch_event(QueueEndEvent(self))
                return

            pop_at = randrange(len(self.queue)) if self.shuffle else 0
            track = self.queue.pop(pop_at)

        if start_time is not None:
            if not isinstance(start_time, int) or not 0 <= start_time < track.duration:
                raise ValueError('start_time must be an int with a value equal to, or greater than 0, and less than the track duration')

        if end_time is not None:
            if not isinstance(end_time, int) or not 1 <= end_time <= track.duration:
                raise ValueError('end_time must be an int with a value equal to, or greater than 1, and less than, or equal to the track duration')

        self.current = track
        playable_track = track.track

        if playable_track is None:
            if not isinstance(track, DeferredAudioTrack):
                raise InvalidTrack('Cannot play the AudioTrack as \'track\' is None, and it is not a DeferredAudioTrack!')

            try:
                playable_track = await track.load(self.client)
            except LoadError as load_error:
                await self.client._dispatch_event(TrackLoadFailedEvent(self, track, load_error))

        if playable_track is None:  # This should only fire when a DeferredAudioTrack fails to yield a base64 track string.
            await self.client._dispatch_event(TrackLoadFailedEvent(self, track, None))
            return

        await self.play_track(playable_track, start_time, end_time, no_replace, volume, pause, **kwargs)
        await self.client._dispatch_event(TrackStartEvent(self, track))

        # TODO: Figure out a better solution for the above. Custom player implementations may neglect
        # to dispatch TrackStartEvent leading to confusion and poor user experience.

    async def stop(self):
        """|coro|

        Stops the player.
        """
        await self.node.update_player(self._internal_id, encoded_track=None)
        self.current = None

    async def skip(self):
        """|coro|

        Plays the next track in the queue, if any.
        """
        await self.play()

    def set_loop(self, loop: int):
        """
        Sets whether the player loops between a single track, queue or none.

        0 = off, 1 = single track, 2 = queue.

        Parameters
        ----------
        loop: Literal[0, 1, 2]
            The loop setting. 0 = off, 1 = single track, 2 = queue.
        """
        if not 0 <= loop <= 2:
            raise ValueError('Loop must be 0, 1 or 2.')

        self.loop = loop

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
        """|coro|

        Sets the player's paused state.

        Parameters
        ----------
        pause: :class:`bool`
            Whether to pause the player or not.
        """
        await self.node.update_player(self._internal_id, paused=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        """|coro|

        Sets the player's volume

        Note
        ----
        A limit of 1000 is imposed by Lavalink.

        Parameters
        ----------
        vol: :class:`int`
            The new volume level.
        """
        vol = max(min(vol, 1000), 0)
        await self.node.update_player(self._internal_id, volume=vol)
        self.volume = vol

    async def seek(self, position: int):
        """|coro|

        Seeks to a given position in the track.

        Parameters
        ----------
        position: :class:`int`
            The new position to seek to in milliseconds.
        """
        if not isinstance(position, int):
            raise ValueError('position must be an int!')

        await self.node.update_player(self._internal_id, position=position)

    async def set_filter(self, _filter: FilterT):
        """|coro|

        Applies the corresponding filter within Lavalink.
        This will overwrite the filter if it's already applied.

        Example
        -------
        .. code:: python

            equalizer = Equalizer()
            equalizer.update(bands=[(0, 0.2), (1, 0.3), (2, 0.17)])
            player.set_filter(equalizer)

        Parameters
        ----------
        _filter: :class:`Filter`
            The filter instance to set.

        Raises
        ------
        :class:`TypeError`
            If the provided ``_filter`` is not of type :class:`Filter`.
        """
        if not isinstance(_filter, Filter):
            raise TypeError('Expected object of type Filter, not ' + type(_filter).__name__)

        filter_name = type(_filter).__name__.lower()
        self.filters[filter_name] = _filter
        await self._apply_filters()

    async def update_filter(self, _filter: Type[FilterT], **kwargs):
        """|coro|

        Updates a filter using the upsert method;
        if the filter exists within the player, its values will be updated;
        if the filter does not exist, it will be created with the provided values.

        This will not overwrite any values that have not been provided.

        Example
        -------
        .. code :: python

            player.update_filter(Timescale, speed=1.5)
            # This means that, if the Timescale filter is already applied
            # and it already has set values of "speed=1, pitch=1.2", pitch will remain
            # the same, however speed will be changed to 1.5 so the result is
            # "speed=1.5, pitch=1.2"

        Parameters
        ----------
        _filter: Type[:class:`Filter`]
            The filter class (**not** an instance of, see above example) to upsert.
        **kwargs: :class:`any`
            The kwargs to pass to the filter.

        Raises
        ------
        :class:`TypeError`
            If the provided ``_filter`` is not of type :class:`Filter`.
        """
        if isinstance(_filter, Filter):
            raise TypeError('Expected class of type Filter, not an instance of ' + type(_filter).__name__)

        if not issubclass(_filter, Filter):
            raise TypeError('Expected subclass of type Filter, not ' + _filter.__name__)

        filter_name = _filter.__name__.lower()

        filter_instance = self.filters.get(filter_name, _filter())
        filter_instance.update(**kwargs)
        self.filters[filter_name] = filter_instance
        await self._apply_filters()

    def get_filter(self, _filter: Union[Type[FilterT], str]):
        """
        Returns the corresponding filter, if it's enabled.

        Example
        -------
        .. code:: python

            from lavalink.filters import Timescale
            timescale = player.get_filter(Timescale)
            # or
            timescale = player.get_filter('timescale')

        Parameters
        ----------
        _filter: Union[Type[:class:`Filter`], :class:`str`]
            The filter name, or filter class (**not** an instance of, see above example), to get.

        Returns
        -------
        Optional[:class:`Filter`]
        """
        if isinstance(_filter, str):
            filter_name = _filter
        elif isinstance(_filter, Filter):  # User passed an instance of.
            filter_name = type(_filter).__name__
        else:
            if not issubclass(_filter, Filter):
                raise TypeError('Expected subclass of type Filter, not ' + _filter.__name__)

            filter_name = _filter.__name__

        return self.filters.get(filter_name.lower(), None)

    async def remove_filter(self, _filter: Union[Type[FilterT], str]):
        """|coro|

        Removes a filter from the player, undoing any effects applied to the audio.

        Example
        -------
        .. code:: python

            player.remove_filter(Timescale)
            # or
            player.remove_filter('timescale')

        Parameters
        ----------
        _filter: Union[Type[:class:`Filter`], :class:`str`]
            The filter name, or filter class (**not** an instance of, see above example), to remove.
        """
        if isinstance(_filter, str):
            filter_name = _filter
        elif isinstance(_filter, Filter):  # User passed an instance of.
            filter_name = type(_filter).__name__
        else:
            if not issubclass(_filter, Filter):
                raise TypeError('Expected subclass of type Filter, not ' + _filter.__name__)

            filter_name = _filter.__name__

        fn_lowered = filter_name.lower()

        if fn_lowered in self.filters:
            self.filters.pop(fn_lowered)
            await self._apply_filters()

    async def clear_filters(self):
        """|coro|

        Clears all currently-enabled filters.
        """
        self.filters.clear()
        await self._apply_filters()

    async def _apply_filters(self):
        await self.node.update_player(self._internal_id, filters=list(self.filters.values()))

    async def _handle_event(self, event):
        """
        Handles the given event as necessary.

        Parameters
        ----------
        event: :class:`Event`
            The event that will be handled.
        """
        # A track throws loadFailed when it fails to provide any audio before throwing an exception.
        # A TrackStuckEvent is not proceeded by a TrackEndEvent. In theory, you could ignore a TrackStuckEvent
        # and hope that a track will eventually play, however, it's unlikely.

        if isinstance(event, TrackStuckEvent) or isinstance(event, TrackEndEvent) and event.reason.may_start_next():
            try:
                await self.play()
            except RequestError as re:
                await self.client._dispatch_event(PlayerErrorEvent(self, re))
                _log.exception('[DefaultPlayer:%d] Encountered a request error whilst starting a new track.', self.guild_id)

    async def _update_state(self, state: dict):
        """
        Updates the position of the player.

        Parameters
        ----------
        state: :class:`dict`
            The state that is given to update.
        """
        self._last_update = int(time() * 1000)
        self._last_position = state.get('position', 0)
        self.position_timestamp = state.get('time', 0)

    async def node_unavailable(self):
        """|coro|

        Called when a player's node becomes unavailable.
        Useful for changing player state before it's moved to another node.
        """
        self._internal_pause = True

    async def change_node(self, node: 'Node'):
        """|coro|

        Changes the player's node

        Parameters
        ----------
        node: :class:`Node`
            The node the player is changed to.
        """
        if self.node.available:
            await self.node.destroy_player(self._internal_id)

        old_node = self.node
        self.node = node

        if self._voice_state:
            await self._dispatch_voice_update()

        if self.current:
            playable_track = self.current.track

            if isinstance(self.current, DeferredAudioTrack) and playable_track is None:
                playable_track = await self.current.load(self.client)

            await self.node.update_player(self._internal_id, encoded_track=playable_track, position=self.position,
                                          paused=self.paused, volume=self.volume)
            self._last_update = int(time() * 1000)

        self._internal_pause = False

        if self.filters:
            await self._apply_filters()

        await self.client._dispatch_event(NodeChangedEvent(self, old_node, node))

    def __repr__(self):
        return '<DefaultPlayer volume={0.volume} current={0.current}>'.format(self)
