import json
from abc import ABC, abstractmethod
from random import randrange

from .AudioTrack import *
from .Events import *
from .Player import *


class PlayerManager:
    def __init__(self, lavalink):
        self.lavalink = lavalink
        self._players = {}

    def __len__(self):
        return len(self._players)

    def __getitem__(self, item):
        return self._players.get(item, None)

    def __contains__(self, item):
        return item in self._players

    def find(self, predicate):
        """ Returns the first player in the list based on the given filter predicate. Could be None """
        found = self.find_all(predicate)
        return found[0] if found else None

    def find_all(self, predicate):
        """ Returns a list of players based on the given filter predicate """
        return list(filter(predicate, self._players.values()))

    def get(self, guild_id):
        """ Returns a player from the cache, or creates one if it does not exist """
        if guild_id not in self._players:
            p = Player(lavalink=self.lavalink, guild_id=guild_id)
            self._players[guild_id] = p

        return self._players[guild_id]

    def has(self, guild_id) -> bool:
        """ Returns the presence of a player in the cache """
        return guild_id in self._players

    def clear(self):
        """ Removes all of the players from the cache """
        self._players.clear()

    def use_player(self, player):
        """ Not implemented """
        raise NotImplementedError  # :)


class BasePlayer(ABC):
    def __init__(self, guild_id: int):
        self.node = None  # later
        self.guild_id = str(guild_id)

    @property
    @abstractmethod
    def is_playing(self):
        return False

    @abstractmethod
    async def _handle_event(self, event):
        raise NotImplementedError


class DefaultPlayer(BasePlayer):
    def __init__(self, lavalink, guild_id: int):
        super().__init__(guild_id)
        self._lavalink = lavalink
        self._user_data = {}
        self.guild_id = str(guild_id)
        self.channel_id = None

        self.paused = False
        self.position = 0
        self.position_timestamp = 0
        self.volume = 100
        self.shuffle = False
        self.repeat = False

        self.queue = []
        self.current = None

    @property
    def is_playing(self):
        """ Returns the player's track state """
        return self.connected_channel is not None and self.current is not None

    @property
    def is_connected(self):
        """ Returns the player's connection state """
        return self.connected_channel is not None

    @property
    def connected_channel(self):
        """ Returns the voicechannel the player is connected to """
        if not self.channel_id:
            return None

        return self._lavalink.bot.get_channel(int(self.channel_id))

    async def connect(self, channel_id: int):
        """ Connects to a voicechannel """
        payload = {
            'op': 4,
            'd': {
                'guild_id': self.guild_id,
                'channel_id': str(channel_id),
                'self_mute': False,
                'self_deaf': False
            }
        }
        await self._lavalink.bot._connection._get_websocket(int(self.guild_id)).send(json.dumps(payload))

    async def disconnect(self):
        """ Disconnects from the voicechannel, if any """
        if not self.is_connected:
            return

        await self.stop()

        payload = {
            'op': 4,
            'd': {
                'guild_id': self.guild_id,
                'channel_id': None,
                'self_mute': False,
                'self_deaf': False
            }
        }

        await self._lavalink.bot._connection._get_websocket(int(self.guild_id)).send(json.dumps(payload))

    def store(self, key: object, value: object):
        """ Stores custom user data """
        self._user_data.update({key: value})

    def fetch(self, key: object, default=None):
        """ Retrieves the related value from the stored user data """
        return self._user_data.get(key, default)

    def add(self, requester: int, track: dict):
        """ Adds a track to the queue """
        self.queue.append(AudioTrack().build(track, requester))

    async def play(self):
        """ Plays the first track in the queue, if any """
        if self.repeat and self.current is not None:
            self.queue.append(self.current)

        self.current = None
        self.position = 0
        self.paused = False

        if not self.queue:
            await self.stop()
            await self._lavalink.dispatch_event('QueueEndEvent', self.guild_id)
        else:
            if self.shuffle:
                track = self.queue.pop(randrange(len(self.queue)))
            else:
                track = self.queue.pop(0)

            self.current = track
            await self._lavalink.ws.send(op='play', guildId=self.guild_id, track=track.track)
            await self._lavalink.dispatch_event('TrackStartEvent', self.guild_id)

    async def stop(self):
        """ Stops the player, if playing """
        await self._lavalink.ws.send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        """ Moves the player onto the next track in the queue """
        await self.play()

    async def set_pause(self, pause: bool):
        """ Sets the player's paused state """
        await self._lavalink.ws.send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        """ Sets the player's volume (150% limit imposed by lavalink) """
        self.volume = max(min(vol, 150), 0)
        await self._lavalink.ws.send(op='volume', guildId=self.guild_id, volume=self.volume)

    async def seek(self, pos: int):
        """ Seeks to a given position in the track """
        await self._lavalink.ws.send(op='seek', guildId=self.guild_id, position=pos)

    async def _handle_event(self, event):
        if isinstance(event, (TrackStartEvent, TrackExceptionEvent)) or \
                isinstance(event, TrackEndEvent) and event.reason == 'FINISHED':
                await self.play()
