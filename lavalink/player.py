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
from typing import (TYPE_CHECKING, Any, Dict, List, Optional, Type,  # Literal
                    TypeVar, Union)

from .abc import BasePlayer, DeferredAudioTrack
from .common import MISSING
from .errors import ClientError, RequestError
from .events import (Event, NodeChangedEvent, PlayerErrorEvent, QueueEndEvent,
                     TrackEndEvent, TrackStuckEvent)
from .filters import Filter
from .server import AudioTrack, RawPlayerState

if TYPE_CHECKING:
    from .node import Node

__all__ = (
    "DefaultPlayer",
)

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

        assert self.current is not None

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

    def fetch(self, key: object, default=None) -> Any:
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
            requester: int = 0, index: Optional[int] = None):
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
        track = AudioTrack(track, requester) if isinstance(track, dict) else track

        if requester != 0:
            track.requester = requester

        if index is None:
            self.queue.append(track)
        else:
            self.queue.insert(index, track)

    async def play(self,
                   track: Optional[Union[AudioTrack, 'DeferredAudioTrack', Dict[str, Union[Optional[str], bool, int]]]] = None,
                   start_time: int = MISSING,
                   end_time: int = MISSING,
                   no_replace: bool = MISSING,
                   volume: int = MISSING,
                   pause: bool = MISSING,
                   **kwargs):
        """|coro|

        Plays the given track.

        This method differs from :func:`BasePlayer.play_track` in that it contains additional logic
        to handle certain attributes, such as ``loop``, ``shuffle``, and loading a base64 string from :class:`DeferredAudioTrack`.

        Warning
        -------
        Multiple calls to this method within a short timeframe could cause issues with the player's
        internal state, which can cause errors when processing a :class:`TrackStartEvent`.

        Parameters
        ----------
        track: Optional[Union[:class:`DeferredAudioTrack`, :class:`AudioTrack`, Dict[str, Union[Optional[str], bool, int]]]]
            The track to play. If left unspecified, this will default to the first track in the queue. Defaults to ``None``
            which plays the next song in queue. Accepts either an AudioTrack or a dict representing a track
            returned from Lavalink.
        start_time: :class:`int`
            The number of milliseconds to offset the track by.
            If left unspecified, the track will start from the beginning.
        end_time: :class:`int`
            The position at which the track should stop playing.
            This is an absolute position, so if you want the track to stop at 1 minute, you would pass 60000.
            If left unspecified, the track will play through to the end.
        no_replace: :class:`bool`
            If set to true, operation will be ignored if the player already has a current track.
            If left unspecified, the currently playing track will always be replaced.
        volume: :class:`int`
            The initial volume to set. This is useful for changing the volume between tracks etc.
            If left unspecified, the volume will remain at its current setting.
        pause: :class:`bool`
            Whether to immediately pause the track after loading it. Defaults to ``False``.
        **kwargs: Any
            The kwargs to use when playing. You can specify any extra parameters that may be
            used by plugins, which offer extra features not supported out-of-the-box by Lavalink.py.

        Raises
        ------
        :class:`ValueError`
            If invalid values were provided for ``start_time`` or ``end_time``.
        :class:`TypeError`
            If wrong types were provided for ``no_replace``, ``volume`` or ``pause``.
        """
        if no_replace is True and self.is_playing:
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

        if pause is not MISSING and isinstance(pause, bool):
            self.paused = pause

        if not track:
            if not self.queue:
                await self.stop()  # Also sets current to None.
                self.client._dispatch_event(QueueEndEvent(self))
                return

            pop_at = randrange(len(self.queue)) if self.shuffle else 0
            track = self.queue.pop(pop_at)

        if start_time is not MISSING:
            if not isinstance(start_time, int) or not 0 <= start_time < track.duration:
                raise ValueError('start_time must be an int with a value equal to, or greater than 0, and less than the track duration')

            self._last_position = start_time

        if end_time is not MISSING:
            if not isinstance(end_time, int) or not 1 <= end_time <= track.duration:
                raise ValueError('end_time must be an int with a value equal to, or greater than 1, and less than, or equal to the track duration')

        response = await self.play_track(track, start_time, end_time, no_replace,
                                         volume, pause, **kwargs)

        if response is not None:
            self.paused = response['paused']
            self.volume = response['volume']

    async def stop(self):
        """|coro|

        Stops the player.
        """
        await self.node.update_player(guild_id=self._internal_id, encoded_track=None)
        self.current = None

    async def skip(self):
        """|coro|

        Plays the next track in the queue, if any.

        Warning
        -------
        Multiple calls to this method within a short timeframe could cause issues with the player's
        internal state, which can cause errors when processing a :class:`TrackStartEvent`.
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
        await self.node.update_player(guild_id=self._internal_id, paused=pause)
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
        await self.node.update_player(guild_id=self._internal_id, volume=vol)
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

        await self.node.update_player(guild_id=self._internal_id, position=position)

    async def set_filters(self, *filters: Filter, replace: bool = False):
        """|coro|

        This sets multiple filters at once.

        Applies the corresponding filters within Lavalink.
        This will overwrite any identical filters that are already applied.

        Parameters
        ----------
        *filters: :class:`Filter`
            The filters to apply.
        replace: :class:`bool`
            Whether to clear all existing filters.

        Raises
        ------
        :class:`TypeError`
            If any of the provided filters is not of type :class:`Filter`.
        """
        for _filter in filters:
            if not isinstance(_filter, Filter):
                raise TypeError(f'Expected object of type Filter, not {type(_filter).__name__}')

        if replace:
            self.filters.clear()

        for _filter in filters:
            self.filters[type(_filter).__name__.lower()] = _filter

        await self._apply_filters()

    async def set_filter(self, _filter: Filter, *, replace: bool = False):
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
        replace: :class:`bool`
            Whether to clear all existing filters.

        Raises
        ------
        :class:`TypeError`
            If the provided ``_filter`` is not of type :class:`Filter`.
        """
        if not isinstance(_filter, Filter):
            raise TypeError(f'Expected object of type Filter, not {type(_filter).__name__}')

        if replace:
            self.filters.clear()

        self.filters[type(_filter).__name__.lower()] = _filter
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
        **kwargs: Any
            The kwargs to pass to the filter.

        Raises
        ------
        :class:`TypeError`
            If the provided ``_filter`` is not of type :class:`Filter`.
        """
        if isinstance(_filter, Filter):
            raise TypeError(f'Expected class of type Filter, not an instance of {type(_filter).__name__}')

        if not issubclass(_filter, Filter):
            raise TypeError(f'Expected subclass of type Filter, not {_filter.__name__}')

        filter_name = _filter.__name__.lower()

        filter_instance = self.filters.get(filter_name, _filter())  # type: ignore
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
                raise TypeError(f'Expected subclass of type Filter, not {_filter.__name__}')

            filter_name = _filter.__name__

        return self.filters.get(filter_name.lower(), None)

    async def remove_filters(self, *filters: Union[Type[FilterT], str]):
        """|coro|

        Removes multiple filters from the player, undoing any effects applied to the audio.
        This is similar to :func:`remove_filter` but instead allows you to remove multiple filters with one call.

        Parameters
        ----------
        filters: Union[Type[:class:`Filter`], :class:`str`]
            The filters to remove. Can be filter name, or filter class (**not** an instance of).
        """
        for fltr in filters:
            await self.remove_filter(fltr)

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
                raise TypeError(f'Expected subclass of type Filter, not {_filter.__name__}')

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
        await self.node.update_player(guild_id=self._internal_id, filters=list(self.filters.values()))

    async def handle_event(self, event: Event):
        """
        Handles the given event as necessary.

        Parameters
        ----------
        event: :class:`Event`
            The event to handle.
        """
        # A track throws loadFailed when it fails to provide any audio before throwing an exception.
        # A TrackStuckEvent is not proceeded by a TrackEndEvent. In theory, you could ignore a TrackStuckEvent
        # and hope that a track will eventually play, however, it's unlikely.

        if isinstance(event, TrackStuckEvent) or isinstance(event, TrackEndEvent) and event.reason.may_start_next():
            try:
                await self.play()
            except RequestError as error:
                self.client._dispatch_event(PlayerErrorEvent(self, error))
                _log.exception('[DefaultPlayer:%d] Encountered a request error whilst starting a new track.', self.guild_id)

    async def update_state(self, state: RawPlayerState):
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
        self._last_position = self.position
        self._internal_pause = True

    async def change_node(self, node: 'Node'):
        """|coro|

        Changes the player's node

        Parameters
        ----------
        node: :class:`Node`
            The node the player is changed to.
        """
        old_node = self.node
        self.node = node

        last_position = self.position

        try:
            await self.node.destroy_player(self._internal_id)
        except (ClientError, RequestError):
            pass

        try:
            if self._voice_state:
                await self._dispatch_voice_update()

            if self.current:
                playable_track = self.current.track

                if isinstance(self.current, DeferredAudioTrack) and playable_track is None:
                    playable_track = await self.current.load(self.client)

                self._last_position = last_position  # Ensure that _last_position is correctly set, in case a node sends us bad data.

                await self.node.update_player(guild_id=self._internal_id, encoded_track=playable_track, position=last_position,
                                              paused=self.paused, volume=self.volume)
                self._last_update = int(time() * 1000)

            if self.filters:
                await self._apply_filters()

            self.client._dispatch_event(NodeChangedEvent(self, old_node, node))
        finally:
            self._internal_pause = False

    def __repr__(self):
        return f'<DefaultPlayer volume={self.volume} current={self.current}>'
