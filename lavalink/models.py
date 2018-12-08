from abc import ABC, abstractmethod
from random import randrange
from time import time
from .events import (TrackStartEvent, TrackStuckEvent, TrackExceptionEvent, TrackEndEvent, QueueEndEvent, PlayerUpdateEvent,
                     NodeChangedEvent)  # noqa: F401
from .node import Node


class InvalidTrack(Exception):
    """ This exception will be raised when an invalid track was passed. """
    pass


class TrackNotBuilt(Exception):
    """ This exception will be raised when AudioTrack objects hasn't been built. """
    pass


class AudioTrack:
    __slots__ = ('track', 'identifier', 'is_seekable', 'author', 'duration', 'stream', 'title', 'uri', 'requester',
                 'preferences')

    def __init__(self, requester, **kwargs):
        self.requester = requester
        self.preferences = kwargs

    @classmethod
    def build(cls, track, requester, **kwargs):
        """ Returns an optional AudioTrack. """
        new_track = cls(requester, **kwargs)
        try:
            new_track.track = track['track']
            new_track.identifier = track['info']['identifier']
            new_track.is_seekable = track['info']['isSeekable']
            new_track.author = track['info']['author']
            new_track.duration = track['info']['length']
            new_track.stream = track['info']['isStream']
            new_track.title = track['info']['title']
            new_track.uri = track['info']['uri']

            return new_track
        except KeyError:
            raise InvalidTrack('An invalid track was passed.')

    def __repr__(self):
        if not hasattr(self, 'track'):
            raise TrackNotBuilt
        return '<AudioTrack title={0.title} identifier={0.identifier}>'.format(self)


class NoPreviousTrack(Exception):
    pass


class BasePlayer(ABC):
    def __init__(self, guild_id: int, node: Node):
        self.guild_id = str(guild_id)
        self.node = node
        self._voice_state = {}
        self.channel_id = None

    @abstractmethod
    async def handle_event(self, event):
        raise NotImplementedError

    @abstractmethod
    async def update_state(self, state: dict):
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
    async def change_node(self, node: Node):
        raise NotImplementedError


class DefaultPlayer(BasePlayer):
    def __init__(self, guild_id: int, node: Node):
        super().__init__(guild_id, node)

        self._user_data = {}

        self.paused = False
        self.last_update = 0
        self.last_position = 0
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
        """ Returns whether the player is connected to a voicechannel or not """
        return self.channel_id is not None

    @property
    def position(self):
        """ Returns the position in the track, adjusted for Lavalink's 5-second stats interval. """
        if not self.is_playing:
            return 0

        if self.paused:
            return min(self.last_position, self.current.duration)

        difference = time() * 1000 - self.last_update
        return min(self.last_position + difference, self.current.duration)

    def store(self, key: object, value: object):
        """
        Stores custom user data.
        ----------
        :param key:
            The key of the object to store.
        :param value:
            The object to associate with the key.
        """
        self._user_data.update({key: value})

    def fetch(self, key: object, default=None):
        """
        Retrieves the related value from the stored user data.
        ----------
        :param key:
            The key to fetch.
        :param default:
            The object that should be returned if the key doesn't exist.
        """
        return self._user_data.get(key, default)

    def delete(self, key: object):
        """
        Removes an item from the the stored user data.
        ----------
        :param key:
            The key to delete
        """
        try:
            del self._user_data[key]
        except KeyError:
            pass

    def add(self, requester: int, track: dict, index: int = None):
        """
        Adds a track to the queue.
        ----------
        :param requester:
            The ID of the user who requested the track.
        :param track:
            A dict representing a track returned from Lavalink.
        :param index:
            The index at which to add the track.
            If index is left unspecified, the default behaviour is to append the track.
        """
        if index is None:
            self.queue.append(AudioTrack.build(track, requester))
        else:
            self.queue.insert(index, AudioTrack.build(track, requester))

    async def play(self, track: AudioTrack = None):
        """
        Plays the given track.
        ----------
        :param track:
            The track to play. If left unspecified, this will default
            to the first track in the queue.
        """
        if self.repeat and self.current:
            self.queue.append(self.current)

        self.current = None
        self.last_update = 0
        self.last_position = 0
        self.position_timestamp = 0
        self.paused = False

        if not track:
            if not self.queue:
                await self.stop()
                await self.node._dispatch_event(QueueEndEvent(self))
                return

            if self.shuffle:
                track = self.queue.pop(randrange(len(self.queue)))
            else:
                track = self.queue.pop(0)

        self.current = track
        await self.node._send(op='play', guildId=self.guild_id, track=track.track)
        await self.node._dispatch_event(TrackStartEvent(self, track))

    async def stop(self):
        """ Stops the player. """
        await self.node._send(op='stop', guildId=self.guild_id)
        await self.reset_equalizer()
        self.current = None

    async def skip(self):
        """ Plays the next track in the queue, if any. """
        await self.play()

    async def set_pause(self, pause: bool):
        """
        Sets the player's paused state.
        ----------
        :param pause:
            Whether to pause the player or not
        """
        await self.node._send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        """
        Sets the player's volume (A limit of 1000 is imposed by Lavalink).
        ----------
        :param vol:
            The new volume level.
        """
        self.volume = max(min(vol, 1000), 0)
        await self.node._send(op='volume', guildId=self.guild_id, volume=self.volume)

    async def seek(self, position: int):
        """
        Seeks to a given position in the track.
        ----------
        :param pos:
            The new position to seek to in milliseconds.
        """
        await self.node._send(op='seek', guildId=self.guild_id, position=position)

    async def set_gain(self, band: int, gain: float = 0.0):
        """
        Sets the equalizer band gain to the given amount.
        ----------
        :param band:
            Band number (0-14).
        :param gain:
            A float representing gain of a band (-0.25 to 1.00) Defaults to 0.0.
        """
        await self.set_gains((band, gain))

    async def set_gains(self, *gain_list):
        """
        Modifies the player's equalizer settings.
        ----------
        :param gain_list:
            A list of tuples denoting (`band`, `gain`).
        """
        update_package = []
        for value in gain_list:
            if not isinstance(value, tuple):
                raise TypeError('gain_list must be a list of tuples')

            band = value[0]
            gain = value[1]

            if -1 > value[0] > 15:
                continue

            gain = max(min(float(gain), 1.0), -0.25)
            update_package.append({'band': band, 'gain': gain})
            self.equalizer[band] = gain

        await self.node._send(op='equalizer', guildId=self.guild_id, bands=update_package)

    async def reset_equalizer(self):
        """ Resets equalizer to default values. """
        await self.set_gains(*[(x, 0.0) for x in range(15)])

    async def handle_event(self, event):
        """ Handles the given event as necessary. """
        if isinstance(event, (TrackStuckEvent, TrackExceptionEvent)) or \
                isinstance(event, TrackEndEvent) and event.reason == 'FINISHED':
            await self.play()

    async def update_state(self, state: dict):
        self.last_update = time() * 1000
        self.last_position = state.get('position', 0)
        self.position_timestamp = state.get('time', 0)

        event = PlayerUpdateEvent(self, self.last_position, self.position_timestamp)
        await self.node._dispatch_event(event)

    async def change_node(self, node: Node):
        if self.node.available:
            await self.node._send(op='destroy', guildId=self.guild_id)

        old_node = self.node
        self.node = node

        if self._voice_state:
            await self._dispatch_voice_update()

        if self.current:
            await self.node._send(op='play', guildId=self.guild_id, track=self.current.track, startTime=self.position)
            self.last_update = time() * 1000

            if self.paused:
                await self.node._send(op='pause', guildId=self.guild_id, pause=self.paused)

        if self.volume != 100:
            await self.node._send(op='volume', guildId=self.guild_id, volume=self.volume)

        if any(self.equalizer):  # If any bands of the equalizer was modified
            payload = [{'band': b, 'gain': g} for b, g in enumerate(self.equalizer)]
            await self.node._send(op='equalizer', guildId=self.guild_id, bands=payload)

        await self.node._dispatch_event(NodeChangedEvent(self, old_node, node))
