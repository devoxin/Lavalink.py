import discord
from discord.ext import commands
from utils import lavalink


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.lavalink = lavalink.Client(bot=bot, password='youshallnotpass', loop=self.bot.loop)

        self.state_keys = {}
        self.validator = ['op', 'guildId', 'sessionId', 'event']

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query):
        player = await self.lavalink.get_player(guild_id=ctx.guild.id)

        if not player.is_connected():
            await player.connect(channel_id=ctx.author.voice.channel.id)

        query = query.strip('<>')

        if not query.startswith('http'):
            query = f'ytsearch:{query}'

        tracks = await self.lavalink.get_tracks(query)
        if not tracks:
            return await ctx.send('Nothing found 👀')

        await player.add(requester=ctx.author.id, track=tracks[0], play=True)

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour,
                              title="Track Enqueued",
                              description=f'[{tracks[0]["info"]["title"]}]({tracks[0]["info"]["uri"]})')
        await ctx.send(embed=embed)

    @commands.command(aliases=['forceskip', 'fs'])
    async def skip(self, ctx):
        player = await self.lavalink.get_player(guild_id=ctx.guild.id)
        await player.skip()

    @commands.command(aliases=['np', 'n'])
    async def now(self, ctx):
        player = await self.lavalink.get_player(guild_id=ctx.guild.id)
        song = 'Nothing'
        if player.current:
            pos = lavalink.Utils.format_time(player.position)
            if player.current.stream:
                dur = 'LIVE'
            else:
                dur = lavalink.Utils.format_time(player.current.duration)
            song = f'**[{player.current.title}]({player.current.uri})**\n({pos}/{dur})'

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Now Playing', description=song)
        await ctx.send(embed=embed)

    @commands.command(aliases=['q'])
    async def queue(self, ctx):
        player = await self.lavalink.get_player(guild_id=ctx.guild.id)

        queue_list = 'Nothing queued' if not player.queue else ''
        for track in player.queue:
            queue_list += f'[**{track.title}**]({track.uri})\n'

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour, title='Queue', description=queue_list)
        await ctx.send(embed=embed)
    
    @commands.command()
    async def pause(self, ctx):
        player = await self.lavalink.get_player(guild_id=ctx.guild.id)

        if not player.is_playing():
            return

        await player.set_paused(True)

    @commands.command()
    async def resume(self, ctx):
        player = await self.lavalink.get_player(guild_id=ctx.guild.id)

        if not player.is_playing():
            return

        await player.set_paused(False)

    @commands.command(aliases=['vol'])
    async def volume(self, ctx, volume):
        player = await self.lavalink.get_player(guild_id=ctx.guild.id)

        if not player.is_playing():
            return

        if not lavalink.Utils.is_number(volume):
            return await ctx.send('You didn\'t specify a valid number!')

        await player.set_volume(int(volume))
    
    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx):
        player = await self.lavalink.get_player(guild_id=ctx.guild.id)
        await player.disconnect()

    async def on_voice_server_update(self, data):
        self.state_keys.update({
            'op': 'voiceUpdate',
            'guildId': data.get('guild_id'),
            'event': data
        })

        await self.verify_and_dispatch()

    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id:
            self.state_keys.update({'sessionId': after.session_id})

        await self.verify_and_dispatch()

    async def verify_and_dispatch(self):
        if all(k in self.state_keys for k in self.validator):
            await self.lavalink.dispatch_voice_update(self.state_keys)
            self.state_keys.clear()


def setup(bot):
    bot.add_cog(Music(bot))
