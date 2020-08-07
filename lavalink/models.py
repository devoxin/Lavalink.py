import typing
from abc import ABC, abstractmethod
from random import randrange
from time import time

from .events import (NodeChangedEvent, PlayerUpdateEvent,  # noqa: F401
                     QueueEndEvent, TrackEndEvent, TrackExceptionEvent,
                     TrackStartEvent, TrackStuckEvent)
from .exceptions import InvalidTrack


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
            self.track = data['track']
            self.identifier = data['info']['identifier']
            self.is_seekable = data['info']['isSeekable']
            self.author = data['info']['author']
            self.duration = data['info']['length']
            self.stream = data['info']['isStream']
            self.title = data['info']['title']
            self.uri = data['info']['uri']
            self.requester = requester
            self.extra = extra
        except KeyError as ke:
            missing_key, = ke.args
            raise InvalidTrack('Cannot build a track from partial data! (Missing key: {})'.format(missing_key)) from None

    def __getitem__(self, name):
        return super().__getattribute__(name)

    def __repr__(self):
        return '<AudioTrack title={0.title} identifier={0.identifier}>'.format(self)


class BasePlayer(ABC):
    """
    Represents the BasePlayer all players must be inherited from.

    Attributes
    ----------
    guild_id: :class:`str`
        The guild id of the player.
    node: :class:`Node`
        The node that the player is connected to.
    """
    def __init__(self, guild_id, node):
        self.guild_id = str(guild_id)
        self.node = node
        self._original_node = None  # This is used internally for failover.
        self._voice_state = {}
        self.channel_id = None

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

        self.channel_id = data['channel_id']

        if not self.channel_id:  # We're disconnecting
            self._voice_state.clear()
            return

        await self._dispatch_voice_update()

    async def _dispatch_voice_update(self):
        if {'sessionId', 'event'} == self._voice_state.keys():
            await self.node._send(op='voiceUpdate', guildId=self.guild_id, **self._voice_state)

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
        The position of how far a track has gone.
    volume: :class:`int`
        The volume at which the player is playing at.
    shuffle: :class:`bool`
        Whether or not to mix the queue up in a random playing order.
    repeat: :class:`bool`
        Whether or not to continuously to play a track.
    equalizer: :class:`list`
        The changes to audio frequencies on tracks.
    queue: :class:`list`
        The order of which tracks are played.
    current: :class:``AudioTrack`
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
        self.equalizer = [0.0 for x in range(15)]  # 0-14, -0.25 - 1.0

        self.queue = []
        self.current = None

    @property
    def is_playing(self):
        """ Returns the player's track state. """
        return self.is_connected and self.current is not None

    @property
    def is_connected(self):
        """ Returns whether the player is connected to a voicechannel or not. """
        return self.channel_id is not None

    @property
    def position(self):
        """ Returns the position in the track, adjusted for Lavalink's 5-second stats interval. """
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

    def add(self, requester: int, track: typing.Union[AudioTrack, dict], index: int = None):
        """
        Adds a track to the queue.

        Parameters
        ----------
        requester: :class:`int`
            The ID of the user who requested the track.
        track: Union[:class:`AudioTrack`, :class:`dict`]
            The track to add. Accepts either an AudioTrack or
            a dict representing a track returned from Lavalink.
        index: Optional[:class:`int`]
            The index at which to add the track.
            If index is left unspecified, the default behaviour is to append the track. Defaults to `None`.
        """
        at = AudioTrack(track, requester) if isinstance(track, dict) else track

        if index is None:
            self.queue.append(at)
        else:
            self.queue.insert(index, at)

    async def play(self, track: typing.Union[AudioTrack, dict] = None, start_time: int = 0, end_time: int = 0, no_replace: bool = False):
        """
        Plays the given track.

        Parameters
        ----------
        track: Optional[Union[:class:`AudioTrack`, :class:`dict`]]
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
        await self.node._send(op='play', guildId=self.guild_id, track=track.track, **options)
        await self.node._dispatch_event(TrackStartEvent(self, track))

    async def stop(self):
        """ Stops the player. """
        await self.node._send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        """ Plays the next track in the queue, if any. """
        await self.play()

    def set_repeat(self, repeat: bool):
        """
        Sets the player's repeat state.
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
        await self.node._send(op='pause', guildId=self.guild_id, pause=pause)
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
        self.volume = max(min(vol, 1000), 0)
        await self.node._send(op='volume', guildId=self.guild_id, volume=self.volume)

    async def seek(self, position: int):
        """
        Seeks to a given position in the track.

        Parameters
        ----------
        position: :class:`int`
            The new position to seek to in milliseconds.
        """
        await self.node._send(op='seek', guildId=self.guild_id, position=position)

    async def set_gain(self, band: int, gain: float = 0.0):
        """
        Sets the equalizer band gain to the given amount.

        Parameters
        ----------
        band: :class:`int`
            Band number (0-14).
        gain: Optional[:class:`float`]
            A float representing gain of a band (-0.25 to 1.00). Defaults to 0.0.
        """
        await self.set_gains((band, gain))

    async def set_gains(self, *gain_list):
        """
        Modifies the player's equalizer settings.

        Parameters
        ----------
        gain_list: :class:`any`
            A list of tuples denoting (`band`, `gain`).
        """
        update_package = []
        for value in gain_list:
            if not isinstance(value, tuple):
                raise TypeError('gain_list must be a list of tuples')

            band = value[0]
            gain = value[1]

            if not -1 < value[0] < 15:
                raise IndexError('{} is an invalid band, must be 0-14'.format(band))

            gain = max(min(float(gain), 1.0), -0.25)
            update_package.append({'band': band, 'gain': gain})
            self.equalizer[band] = gain

        await self.node._send(op='equalizer', guildId=self.guild_id, bands=update_package)

    async def reset_equalizer(self):
        """ Resets equalizer to default values. """
        await self.set_gains(*[(x, 0.0) for x in range(15)])

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

        event = PlayerUpdateEvent(self, self._last_position, self.position_timestamp)
        await self.node._dispatch_event(event)

    async def change_node(self, node):
        """
        Changes the player's node

        Parameters
        ----------
        node: :class:`Node`
            The node the player is changed to.
        """
        if self.node.available:
            await self.node._send(op='destroy', guildId=self.guild_id)

        old_node = self.node
        self.node = node

        if self._voice_state:
            await self._dispatch_voice_update()

        if self.current:
            await self.node._send(op='play', guildId=self.guild_id, track=self.current.track, startTime=self.position)
            self._last_update = time() * 1000

            if self.paused:
                await self.node._send(op='pause', guildId=self.guild_id, pause=self.paused)

        if self.volume != 100:
            await self.node._send(op='volume', guildId=self.guild_id, volume=self.volume)

        if any(self.equalizer):  # If any bands of the equalizer was modified
            payload = [{'band': b, 'gain': g} for b, g in enumerate(self.equalizer)]
            await self.node._send(op='equalizer', guildId=self.guild_id, bands=payload)

        await self.node._dispatch_event(NodeChangedEvent(self, old_node, node))
