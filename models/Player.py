from random import randrange

from . import AudioTrack


class Player:
    def __init__(self, bot, guild_id):
        self.bot = bot

        self.shard_id = bot.get_guild(guild_id).shard_id
        self.guild_id = str(guild_id)
        self.channel_id = None

        self.is_connected = lambda: self.channel_id is not None
        self.is_playing = lambda: self.channel_id is not None and self.current is not None
        self.paused = False

        self.position = 0
        self.position_timestamp = 0
        self.volume = 100

        self.queue = []
        self.current = None

        self.shuffle = False
        self.repeat = False

    async def connect(self, channel_id):
        await self.bot.lavalink.client.send(op='connect', guildId=self.guild_id, channelId=str(channel_id))
        self.channel_id = str(channel_id)  # Raceconditions

    async def disconnect(self):
        if not self.is_connected():
            return

        if self.is_playing():
            await self.stop()

        await self.bot.lavalink.client.send(op='disconnect', guildId=self.guild_id)

    async def add(self, requester, track, play=False):
        self.queue.append(await AudioTrack().build(track, requester))

        if play and not self.is_playing():
            await self.play()

    async def play(self):
        if not self.is_connected() or not self.queue:
            if self.is_playing():
                await self.stop()

            self.current = None
            return

        if self.shuffle:
            track = self.queue.pop(randrange(len(self.queue)))
        else:
            track = self.queue.pop(0)

        await self.bot.lavalink.client.send(op='play', guildId=self.guild_id, track=track.track)
        self.current = track

    async def stop(self):
        await self.bot.lavalink.client.send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        await self.play()

    async def set_paused(self, pause):
        await self.bot.lavalink.client.send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol):
        if not isinstance(vol, int):
            return

        if vol < 0:
            vol = 0

        if vol > 150:
            vol = 150

        await self.bot.lavalink.client.send(op='volume', guildId=self.guild_id, volume=vol)
        self.volume = vol
        return vol

    async def seek(self, pos):
        await self.bot.lavalink.client.send(op='seek', guildId=self.guild_id, position=pos)

    async def _on_track_end(self, data):
        self.position = 0
        self.paused = False

        if data.get('reason') == 'FINISHED':
            await self.play()

    async def _validate_join(self, data):
        await self.bot.lavalink.client.send(op='validationRes', guildId=data.get('guildId'), channelId=data.get('channelId', None), valid=True)
