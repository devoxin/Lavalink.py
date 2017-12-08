import asyncio

import discord
from discord.ext import commands
from utils import lavalink


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.lavalink = lavalink.Client(bot=bot, shard_count=len(self.bot.shards), user_id=self.bot.user.id, password='youshallnotpass', loop=self.bot.loop)

        self.state_keys = {}
        self.validator = ['op', 'guildId', 'sessionId', 'event']

        #self.players = {}
        self.player = None

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query):
        # p = await self._get_or_create(guild_id=ctx.guild.id)
        if not self.player:
            await self._get_or_create(ctx.guild.id)
        
        if not self.player.is_connected():
            await self.player.connect(channel_id=ctx.author.voice.channel.id)

        query = query.strip('<>')

        if not query.startswith('http'):
            query = f'ytsearch:{query}'

        tracks = await self.lavalink.get_tracks(query)
        await self.player.add(track=tracks[0], play=True)

        embed = discord.Embed(title="Enqueued", description=f'[{tracks[0]["info"]["title"]}]({tracks[0]["info"]["uri"]})')
        await ctx.send(embed=embed)

    async def _get_or_create(self, guild_id):
        # if guild_id not in self.players:
        #     p = await self.lavalink.create_player(guild_id=guild_id)
        #     self.players.update({ guild_id: p })
        # else:
        #     p = self.players.get(guild_id)
        # return p
        self.player = await self.lavalink.create_player(guild_id=guild_id)
    
    async def on_voice_server_update(self, data):
        self.state_keys.update({ 
            'op': 'voiceUpdate',
            'guildId': data.get('guild_id'),
            'event': data
        })

        await self.verify_and_dispatch()

    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id:
            self.state_keys.update({ 'sessionId': after.session_id })
        
        await self.verify_and_dispatch()

    async def verify_and_dispatch(self):
        if all(k in self.state_keys for k in self.validator):
            await self.lavalink.dispatch_voice_update(self.state_keys)
            self.state_keys.clear()

def setup(bot):
    bot.add_cog(Music(bot))
