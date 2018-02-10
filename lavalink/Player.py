import json
from random import randrange

from .AudioTrack import *


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

    async def connect(self, channel):
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

        await self.bot._connection._get_websocket(int(self.guild_id)).send(json.dumps(payload))
        self.channel_id = None

    def store(self, key, value):
        """ Stores custom user data """
        self._user_data.update({key: value})

    def fetch(self, key, default=None):
        """ Retrieves the related value from the stored user data """
        return self._user_data.get(key, default)

    async def add(self, requester, track, interrupt=False):
        """ Adds a track to the queue, and plays it immediately if not playing """
        self.queue.append(AudioTrack().build(track, requester))

        if not self.is_playing or interrupt:
            await self.play()

    async def play(self):
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

    async def stop(self):
        """ Stops the player, if playing """
        await self.bot.lavalink.ws.send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        """ Moves the player onto the next track in the queue """
        await self.play()

    async def set_pause(self, pause: bool):
        """ Sets the player's paused state """
        await self.bot.lavalink.ws.send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        """ Sets the player's volume (150% limit imposed by lavalink) """
        if isinstance(vol, int):
            self.volume = max(min(vol, 150), 0)

            await self.bot.lavalink.ws.send(op='volume', guildId=self.guild_id, volume=self.volume)
            return self.volume

    async def seek(self, pos: int):
        """ Seeks to a given position in the track """
        await self.bot.lavalink.ws.send(op='seek', guildId=self.guild_id, position=pos)

    async def on_track_end(self, reason):
        if reason == 'FINISHED':
            await self.play()
