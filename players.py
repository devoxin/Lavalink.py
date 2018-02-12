import json
from time import time

from.audio_events import TrackStartEvent, TrackPauseEvent, TrackResumeEvent


class Player:
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.event_adapters = []
        self.guild_id = str(guild_id)
        self.channel_id = None
        self._user_data = {}
        self.paused = False
        self._position = -1
        self._position_timestamp = -1
        self.volume = 100
        self.current = None

    @property
    def position(self):
        if not self.paused:
            diff = time() - self._position_timestamp
            return min(self._position + diff, self.current)
    
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

        return self.bot.get_channel(int(self.channel_id))

    async def connect(self, channel):
        """ Connects to a voice channel. This is sending directly to discord, not to the lavalink node"""
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
        """ Disconnects from the voice channel, if any. This is sending directly to discord, not to the lavalink node"""
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

    async def play(self, track):
        """ Plays a requested track"""
        await self.bot.lavalink.ws.send(op='play', guildId=self.guild_id, track=track.track)
        self.current = track
        await self.trigger_event(TrackStartEvent(self, track))

    async def stop(self):
        """ Stops the player, if playing """
        await self.bot.lavalink.ws.send(op='stop', guildId=self.guild_id)
        self.current = None

    async def destroy(self):
        """ Stops the player, if playing """
        await self.bot.lavalink.ws.send(op='destroy', guildId=self.guild_id)
        self.current = None

    async def set_pause(self, pause: bool):
        """ Sets the player's paused state """
        if pause == self.paused:
            return
        await self.bot.lavalink.ws.send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause
        if pause:
            await self.trigger_event(TrackPauseEvent(self))
        else:
            await self.trigger_event(TrackResumeEvent(self))

    async def set_volume(self, vol: int):
        """ Sets the player's volume (150% limit imposed by lavalink) """
        self.volume = max(min(vol, 150), 0)

        await self.bot.lavalink.ws.send(op='volume', guildId=self.guild_id, volume=self.volume)

    async def seek(self, pos: int):
        """ Seeks to a given position in the track """
        await self.bot.lavalink.ws.send(op='seek', guildId=self.guild_id, position=pos)

    async def trigger_event(self, event):
        """ Triggering an an event, using event adapters"""
        if not self.event_adapters:
            return
        for i in self.event_adapters:
            i.on_event(event)


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

    def get(self, ctx):
        """ Returns a player from the cache, or creates one if it does not exist """
        guild_id = ctx.guild.id
        if guild_id not in self._players:
            p = Player(bot=self.bot, guild_id=guild_id)
            self._players[guild_id] = p

        return self._players[guild_id]

    def has(self, guild_id):
        """ Returns the presence of a player in the cache """
        return guild_id in self._players

    def clear(self):
        """ Removes all of the players from the cache """
        self._players.clear()

    def get_playing(self):
        """ Returns the amount of players that are currently playing """
        return len([p for p in self._players.values() if p.is_playing])

