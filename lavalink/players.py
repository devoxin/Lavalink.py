import json
from random import randrange

from .audio_track import *
from abc import ABC, abstractmethod


class AbstractPlayer(ABC):

    @abstractmethod
    async def _on_track_end(self):
        raise NotImplementedError

    @abstractmethod
    async def _on_track_start(self):
        raise NotImplementedError


class Player:
    def __init__(self, bot, guild_id: int):
        self.bot = bot
        self.guild_id = str(guild_id)
        self.channel_id = None
        self._user_data = {}

        self.paused = False
        self.position = 0
        self.position_timestamp = 0
        self.volume = 100
        self.shuffle = False
        self.repeat = False

        self.queue = []
        self.current = None

    @property
    def is_playing(self) -> bool:
        """ Returns the player's track state """
        return self.connected_channel is not None and self.current is not None

    @property
    def is_connected(self) -> bool:
        """ Returns the player's connection state """
        return self.connected_channel is not None

    @property
    def connected_channel(self):
        """ Returns the voicechannel the player is connected to """
        if not self.channel_id:
            return None

        return self.bot.get_channel(int(self.channel_id))

    async def connect(self, channel) -> None:
        """ Connects to a voicechannel """
        payload = {
            'op': 4,
            'd': {
                'guild_id': self.guild_id,
                'channel_id': str(channel.id),
                'self_mute': False,
                'self_deaf': False
            }
        }
        await self.bot._connection._get_websocket(int(self.guild_id)).send(json.dumps(payload))
        self.channel_id = str(channel.id)

    async def disconnect(self) -> None:
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

        await self.bot._connection._get_websocket(int(self.guild_id)).send(json.dumps(payload))
        self.channel_id = None

    def store(self, key: object, value: object) -> None:
        """ Stores custom user data """
        self._user_data.update({key: value})

    def fetch(self, key: object, default=None) -> object:
        """ Retrieves the related value from the stored user data """
        return self._user_data.get(key, default)

    def add(self, requester: int, track: dict) -> None:
        """ Adds a track to the queue """
        self.queue.append(AudioTrack(track, requester))

    async def add_and_play(self, requester: int, track: dict) -> None:
        """ Adds a track to the queue and then starts playing if nothing else is playing """
        self.add(requester, track)

        if not self.is_playing:
            await self.play()

    async def play(self) -> None:
        """ Plays the first track in the queue, if any """
        self.current = None
        self.position = 0
        self.paused = False

        if not self.queue:
            await self.stop()
            await self.bot.lavalink.client._trigger_event('QueueEndEvent', self.guild_id)
        else:
            if self.shuffle:
                track = self.queue.pop(randrange(len(self.queue)))
            else:
                track = self.queue.pop(0)

            self.current = track
            await self.bot.lavalink.ws.send(op='play', guildId=self.guild_id, track=track.track)
            await self.bot.lavalink.client._trigger_event('TrackStartEvent', self.guild_id)

    async def stop(self) -> None:
        """ Stops the player, if playing """
        await self.bot.lavalink.ws.send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self) -> None:
        """ Moves the player onto the next track in the queue """
        await self.play()

    async def set_pause(self, pause: bool) -> None:
        """ Sets the player's paused state """
        await self.bot.lavalink.ws.send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int) -> None:
        """ Sets the player's volume (150% limit imposed by lavalink) """
        self.volume = max(min(vol, 150), 0)

        await self.bot.lavalink.ws.send(op='volume', guildId=self.guild_id, volume=self.volume)

    async def seek(self, pos: int) -> None:
        """ Seeks to a given position in the track """
        await self.bot.lavalink.ws.send(op='seek', guildId=self.guild_id, position=pos)

    async def _on_track_end(self, reason: str):
        if reason in ['FINISHED', 'TrackStuckEvent', 'TrackExceptionEvent']:
            await self.play()

class PlayerManager:
    def __init__(self, bot):
        self.bot = bot
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
        return list(filter(predicate, self._players))

    def get(self, guild_id):
        """ Returns a player from the cache, or creates one if it does not exist """
        if guild_id not in self._players:
            p = Player(bot=self.bot, guild_id=guild_id)
            self._players[guild_id] = p

        return self._players[guild_id]

    def has(self, guild_id) -> bool:
        """ Returns the presence of a player in the cache """
        return guild_id in self._players

    def clear(self):
        """ Removes all of the players from the cache """
        self._players.clear()

    def get_playing(self):
        """ Returns the amount of players that are currently playing """
        return len([p for p in self._players.values() if p.is_playing])

    def use_player(self, player):
        """ Not implemented """
        raise NotImplementedError  # :)
