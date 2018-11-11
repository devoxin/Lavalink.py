from abc import ABC, abstractmethod
from random import randrange
from .events import TrackStartEvent, TrackStuckEvent, TrackExceptionEvent, TrackEndEvent, QueueEndEvent
from .node import Node


class InvalidTrack(Exception):
    """ This exception will be raised when an invalid track was passed. """
    pass


class TrackNotBuilt(Exception):
    """ This exception will be raised when AudioTrack objects hasn't been built. """
    pass


class AudioTrack:
    __slots__ = ('track', 'identifier', 'can_seek', 'author', 'duration', 'stream', 'title', 'uri', 'requester',
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
            new_track.can_seek = track['info']['isSeekable']
            new_track.author = track['info']['author']
            new_track.duration = track['info']['length']
            new_track.stream = track['info']['isStream']
            new_track.title = track['info']['title']
            new_track.uri = track['info']['uri']

            return new_track
        except KeyError:
            raise InvalidTrack('An invalid track was passed.')

    @property
    def thumbnail(self):
        """ Returns the video thumbnail. Could be an empty string. """
        if not hasattr(self, 'track'):
            raise TrackNotBuilt
        if 'youtube' in self.uri:
            return "https://img.youtube.com/vi/{}/default.jpg".format(self.identifier)

        return ""

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

    def cleanup(self):
        pass

    async def _voice_server_update(self, data):
        self._voice_state.update({
            'event': data
        })

        if {'sessionId', 'event'} == self._voice_state.keys():
            await self.node._send(op='voiceUpdate', guildId=self.guild_id, **self._voice_state)

    async def _voice_state_update(self, data):
        self._voice_state.update({
            'sessionId': data['session_id']
        })

        self.channel_id = data['channel_id']

        if {'sessionId', 'event'} == self._voice_state.keys():
            await self.node._send(op='voiceUpdate', guildId=self.guild_id, **self._voice_state)


class DefaultPlayer(BasePlayer):
    def __init__(self, guild_id: int, node: Node):
        super().__init__(guild_id, node)

        self._user_data = {}

        self.paused = False
        self.position = 0
        self.position_timestamp = 0
        self.volume = 100
        self.shuffle = False
        self.repeat = False

        self.queue = []
        self.current = None
        self.previous = None

    @property
    def is_playing(self):
        """ Returns the player's track state. """
        return self.is_connected and self.current is not None

    @property
    def is_connected(self):
        """ Returns whether the player is connected to a voicechannel or not """
        return self.channel_id is not None

    def store(self, key: object, value: object):
        """ Stores custom user data. """
        self._user_data.update({key: value})

    def fetch(self, key: object, default=None):
        """ Retrieves the related value from the stored user data. """
        return self._user_data.get(key, default)

    def delete(self, key: object):
        """ Removes an item from the the stored user data. """
        try:
            del self._user_data[key]
        except KeyError:
            pass

    def add(self, requester: int, track: dict, index: int = 0):
        """
        Adds a track to the queue
        ----------
        :param requester:
            The ID of the user who requested the track
        :param track:
            A dict representing a track returned from Lavalink
        :param index:
            The index at which to add the track. Defaults to 0
        """
        self.queue.insert(index, AudioTrack.build(track, requester))

    async def play(self, track_index: int = 0, ignore_shuffle: bool = False):
        """ Plays the first track in the queue, if any or plays a track from the specified index in the queue. """
        if self.repeat and self.current:
            self.queue.append(self.current)

        self.previous = self.current
        self.current = None
        self.position = 0
        self.paused = False

        if not self.queue:
            await self.stop()
            #  await self._lavalink.dispatch_event(QueueEndEvent(self))
        else:
            if self.shuffle and not ignore_shuffle:
                track = self.queue.pop(randrange(len(self.queue)))
            else:
                track = self.queue.pop(min(track_index, len(self.queue) - 1))

            self.current = track
            await self.node._send(op='play', guildId=self.guild_id, track=track.track)
            #  await self._lavalink.dispatch_event(TrackStartEvent(self, track))

    async def play_now(self, requester: int, track: dict):
        """ Add track and play it. """
        self.add_next(requester, track)
        await self.play(ignore_shuffle=True)

    async def play_at(self, index: int):
        """ Play the queue from a specific point. Disregards tracks before the index. """
        self.queue = self.queue[min(index, len(self.queue) - 1):len(self.queue)]
        await self.play(ignore_shuffle=True)

    async def play_previous(self):
        """ Plays previous track if it exist, if it doesn't raises a NoPreviousTrack error. """
        if not self.previous:
            raise NoPreviousTrack
        self.queue.insert(0, self.previous)
        await self.play(ignore_shuffle=True)

    async def stop(self):
        """ Stops the player, if playing. """
        await self.node._send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        """ Plays the next track in the queue, if any. """
        await self.play()

    async def set_pause(self, pause: bool):
        """ Sets the player's paused state. """
        await self.node._send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        """ Sets the player's volume (A limit of 1000 is imposed by Lavalink). """
        self.volume = max(min(vol, 1000), 0)
        await self.node._send(op='volume', guildId=self.guild_id, volume=self.volume)

    async def seek(self, pos: int):
        """ Seeks to a given position in the track. """
        await self.node._send(op='seek', guildId=self.guild_id, position=pos)

    async def handle_event(self, event):
        """ Makes the player play the next song from the queue if a song has finished or an issue occurred. """
        if isinstance(event, (TrackStuckEvent, TrackExceptionEvent)) or \
                isinstance(event, TrackEndEvent) and event.reason == 'FINISHED':
            await self.play()
