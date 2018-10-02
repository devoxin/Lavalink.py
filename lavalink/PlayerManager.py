from abc import ABC, abstractmethod
from random import randrange

from .AudioTrack import AudioTrack
from .Events import QueueEndEvent, TrackExceptionEvent, TrackEndEvent, TrackStartEvent, TrackStuckEvent


class NoPreviousTrack(Exception):
    pass


class BasePlayer(ABC):
    def __init__(self, lavalink, guild_id: int):
        self.node = None  # later
        self._lavalink = lavalink
        self.guild_id = str(guild_id)

    @abstractmethod
    async def handle_event(self, event):
        raise NotImplementedError

    def cleanup(self):
        pass


class DefaultPlayer(BasePlayer):
    def __init__(self, lavalink, guild_id: int):
        super().__init__(lavalink, guild_id)

        self._user_data = {}
        self.channel_id = None

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
        return self.connected_channel is not None and self.current is not None

    @property
    def is_connected(self):
        """ Returns the player's connection state. """
        return self.connected_channel is not None

    @property
    def connected_channel(self):
        """ Returns the voice channel the player is connected to. """
        if not self.channel_id:
            return None

        return self._lavalink.bot.get_channel(int(self.channel_id))

    async def connect(self, channel_id: int):
        """ Connects to a voice channel. """
        ws = self._lavalink.bot._connection._get_websocket(int(self.guild_id))
        await ws.voice_state(self.guild_id, str(channel_id))

    async def disconnect(self):
        """ Disconnects from the voice channel, if any. """
        if not self.is_connected:
            return

        await self.stop()

        ws = self._lavalink.bot._connection._get_websocket(int(self.guild_id))
        await ws.voice_state(self.guild_id, None)

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

    def add(self, requester: int, track: dict):
        """ Adds a track to the queue. """
        self.queue.append(AudioTrack().build(track, requester))

    def add_next(self, requester: int, track: dict):
        """ Adds a track to beginning of the queue """
        self.queue.insert(0, AudioTrack().build(track, requester))

    def add_at(self, index: int, requester: int, track: dict):
        """ Adds a track at a specific index in the queue. """
        self.queue.insert(min(index, len(self.queue) - 1), AudioTrack().build(track, requester))

    async def play(self, track_index: int = 0, ignore_shuffle: bool = False):
        """ Plays the first track in the queue, if any or plays a track from the specified index in the queue. """
        if self.repeat and self.current is not None:
            self.queue.append(self.current)

        self.previous = self.current
        self.current = None
        self.position = 0
        self.paused = False

        if not self.queue:
            await self.stop()
            await self._lavalink.dispatch_event(QueueEndEvent(self))
        else:
            if self.shuffle and not ignore_shuffle:
                track = self.queue.pop(randrange(len(self.queue)))
            else:
                track = self.queue.pop(min(track_index, len(self.queue) - 1))

            self.current = track
            await self._lavalink.ws.send(op='play', guildId=self.guild_id, track=track.track)
            await self._lavalink.dispatch_event(TrackStartEvent(self, track))

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
        if self.previous is None:
            raise NoPreviousTrack
        self.queue.insert(0, self.previous)
        await self.play(ignore_shuffle=True)

    async def stop(self):
        """ Stops the player, if playing. """
        await self._lavalink.ws.send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        """ Plays the next track in the queue, if any. """
        await self.play()

    async def set_pause(self, pause: bool):
        """ Sets the player's paused state. """
        await self._lavalink.ws.send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        """ Sets the player's volume (150% or 1000% limit imposed by lavalink depending on the version). """
        if self._lavalink._server_version <= 2:
            self.volume = max(min(vol, 150), 0)
        else:
            self.volume = max(min(vol, 1000), 0)
        await self._lavalink.ws.send(op='volume', guildId=self.guild_id, volume=self.volume)

    async def seek(self, pos: int):
        """ Seeks to a given position in the track. """
        await self._lavalink.ws.send(op='seek', guildId=self.guild_id, position=pos)

    async def handle_event(self, event):
        """ Makes the player play the next song from the queue if a song has finished or an issue occurred. """
        if isinstance(event, (TrackStuckEvent, TrackExceptionEvent)) or \
                isinstance(event, TrackEndEvent) and event.reason == 'FINISHED':
            await self.play()


class PlayerManager:
    def __init__(self, lavalink, player):
        """
        Instantiates a Player Manager.

        :param lavalink:
            Must be a lavalink.Client object.
        :param player:
            Must implement lavalink.BasePlayer.
        """
        if not issubclass(player, BasePlayer):
            raise ValueError('player must implement lavalink.BasePlayer.')

        self.lavalink = lavalink
        self._player = player
        self._players = {}

    def __len__(self):
        return len(self._players)

    def __getitem__(self, item):
        return self._players.get(item, None)

    def __iter__(self):
        """ Returns a tuple of (guild_id, player). """
        for guild_id, player in self._players.items():
            yield guild_id, player

    def __contains__(self, item):
        """ Returns the presence of a player in the cache. """
        return item in self._players

    def find(self, predicate):
        """ Returns the first player in the list based on the given filter predicate. Could be None. """
        found = self.find_all(predicate)
        return found[0] if found else None

    def find_all(self, predicate):
        """ Returns a list of players based on the given filter predicate. """
        return list(filter(predicate, self._players.values()))

    def get(self, guild_id):
        """ Returns a player from the cache, or creates one if it does not exist. """
        if guild_id not in self._players:
            p = self._player(lavalink=self.lavalink, guild_id=guild_id)
            self._players[guild_id] = p

        return self._players[guild_id]

    def remove(self, guild_id):
        """ Removes a player from the current players. """
        if guild_id in self._players:
            self._players[guild_id].cleanup()
            del self._players[guild_id]

    def clear(self):
        """ Removes all of the players from the cache. """
        self._players.clear()
