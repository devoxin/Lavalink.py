from collections import deque
from enum import Enum
from random import shuffle

import discord

from core.bot import Bot
from lavalink import Client, TrackPauseEvent, TrackResumeEvent, TrackStartEvent, TrackEndEvent, \
    AbstractPlayerEventAdapter, \
    TrackExceptionEvent, TrackStuckEvent, format_time, AudioTrack, LogLevel
from utils.visual import NOTES
from utils.DB import SettingsDB


class UserData(Enum):
    STOPPED = 0
    SKIPPED = 1
    SKIPPED_TO = 2
    UNCHANGED = 3
    REPLACED_AUTOPLAY = 4

    @property
    def may_start_next(self):
        return self.value > 0


class Enqueued:
    def __init__(self, track, requester):
        self.track = track
        self.requester = requester
        self.finished = False

    def __str__(self):
        return f"{self.track.title} (`{format_time(self.track.duration)}`)"


class PlayerHandler(AbstractPlayerEventAdapter):
    def __init__(self, ctx, player):
        self.ctx = ctx
        self.player = player
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.skips = set()
        self.queue = deque()
        self.paused = False
        self.current = None
        self.previous = None

    def embed_current(self):
        track = self.current.track
        title = track.title
        url = track.uri
        requester = self.current.requester.name
        progress = f"{format_time(self.player.position)}/{format_time(track.duration)}"

        embed = discord.Embed(title="Now playing", description=f"[{title}]({url})", color=Bot.COLOR) \
            .add_field(name="Requested by", value=requester, inline=True) \
            .add_field(name="Progress", value=progress, inline=True)
        if "youtube" in url:
            embed.set_thumbnail(url=f"https://img.youtube.com/vi/{track.identifier}/hqdefault.jpg")
        return embed

    def shuffle(self):
        shuffle(self.queue)

    def clear(self):
        self.queue.clear()

    async def add_track(self, audio_track, requester):
        return await self.add_enqueued(Enqueued(audio_track, requester))

    async def add_enqueued(self, enqueued):
        enqueued.track.user_data = UserData.UNCHANGED
        if not self.current:
            self.current = enqueued
            await self.player.play(enqueued.track)
            return -1
        self.queue.append(enqueued)
        return self.queue.index(enqueued)

    async def stop(self):
        self.current = None
        if self.player.current:
            self.player.current.user_data = UserData.STOPPED
            await self.player.stop()
        self.clear()

    async def skip(self):
        self.player.current.user_data = UserData.SKIPPED
        await self.player.stop()

    async def track_pause(self, event: TrackPauseEvent):
        self.paused = True

    async def track_resume(self, event: TrackResumeEvent):
        self.paused = False

    async def track_start(self, event: TrackStartEvent):
        self.skips.clear()
        topic = f"{NOTES} **Now playing** {self.current}"
        settings = await SettingsDB.get_instance().get_guild_settings(self.guild.id)
        text_id = settings.textId
        music_channel = self.guild.get_channel(text_id)
        if music_channel:
            await self.ctx.send(topic)
            try:
                await music_channel.edit(topic=topic)
            except:
                pass
            if settings.tms:
                await music_channel.send(topic)
        else:
            if settings.tms:
                await self.ctx.send(topic)

    async def track_end(self, event: TrackEndEvent):
        user_data = event.track.user_data
        if user_data.may_start_next and len(self.queue) != 0:
            self.previous = self.current
            self.current = self.queue.popleft()
            await self.player.play(self.current.track)
            return
        await self.stop()
        settings = await SettingsDB.get_instance().get_guild_settings(self.guild.id)
        text_id = settings.textId
        music_channel = self.guild.get_channel(text_id)
        if music_channel:
            try:
                await music_channel.edit(topic="Not playing anything right now...")
            except:
                pass

    async def track_exception(self, event: TrackExceptionEvent):
        pass

    async def track_stuck(self, event: TrackStuckEvent):
        pass


class PlayerHandlerManager:
    def __init__(self, bot):
        bot.player_handler_manager = self
        self.bot = bot
        self.lavalink_client = Client(bot=bot, port=8080, log_level=LogLevel.debug,
                                      password='youshallnotpass', loop=self.bot.loop)
        self.lavalink = self.bot.lavalink
        self.player_handlers = {}

    async def get_player_handler(self, ctx):
        if not ctx:
            return self.lavalink.players.get(ctx.guild.id, None)
        player = self.lavalink.players.get(ctx.guild.id)
        if not player.event_adapter:
            player.event_adapter = PlayerHandler(ctx, player)
        return player.event_adapter

    async def search(self, query):
        tracks = await self.lavalink_client.get_tracks(query)
        return [AudioTrack(track) for track in tracks]
