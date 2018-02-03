import math

import discord
from utils import lavalink
from discord.ext import commands


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.lavalink = lavalink.Client(bot=bot, password='youshallnotpass', loop=self.bot.loop)
        # As of 2.0, lavalink.Client will be available via self.bot.lavalink.client

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query):
        if not ctx.guild.voice_client or not ctx.guild.voice_client.channel:
            await ctx.author.voice.channel.connect(reconnect=False)
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        #if not ctx.author.voice or (player.is_connected() and ctx.author.voice.channel.id != int(player.channel_id)):
        #    return await ctx.send('You\'re not in my voicechannel!')

        #if not player.is_connected():
        #    await player.connect(channel_id=ctx.author.voice.channel.id)

        query = query.strip('<>')

        if not query.startswith('http'):
            query = f'ytsearch:{query}'

        tracks = await self.lavalink.get_tracks(query)

        if not tracks:
            return await ctx.send('Nothing found 👀')

        if 'list' in query and 'ytsearch:' not in query:
            for track in tracks:
                await player.add(requester=ctx.author.id, track=track, play=True)

            embed = discord.Embed(colour=ctx.guild.me.top_role.colour,
                                  title="Playlist Enqueued!",
                                  description=f"Imported {len(tracks)} tracks from the playlist :)")
        else:
            await player.add(requester=ctx.author.id, track=tracks[0], play=True)
            embed = discord.Embed(colour=ctx.guild.me.top_role.colour,
                                  title="Track Enqueued",
                                  description=f'[{tracks[0]["info"]["title"]}]({tracks[0]["info"]["uri"]})')

        await ctx.send(embed=embed)

    @commands.command(aliases=['forceskip', 'fs'])
    async def skip(self, ctx):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        if not ctx.author.voice or (player.is_connected() and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        if not player.is_connected():
            await player.connect(channel_id=ctx.author.voice.channel.id)

        await player.skip()
        await ctx.send('⏭ | Skipped.')

    @commands.command(aliases=['np', 'n'])
    async def now(self, ctx):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)
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
    async def queue(self, ctx, page: str=None):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        if not player.queue:
            return await ctx.send('There\'s nothing in the queue! Why not queue something?')

        items_per_page = 10
        pages = math.ceil(len(player.queue) / items_per_page)
        page = lavalink.Utils.get_number(page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue_list = ''

        for i, track in enumerate(player.queue[start:end], start=start):
            queue_list += f'`{i + 1}.` [**{track.title}**]({track.uri})\n'

        embed = discord.Embed(colour=ctx.guild.me.top_role.colour,
                              description=f'**{len(player.queue)} tracks**\n\n{queue_list}')
        embed.set_footer(text=f'Viewing page {page}/{pages}')
        await ctx.send(embed=embed)

    @commands.command(aliases=['resume'])
    async def pause(self, ctx):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        if not player.is_playing():
            return await ctx.send('Nothing playing.')

        if not ctx.author.voice or (player.is_connected() and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        if player.paused:
            await player.set_paused(False)
            await ctx.send('⏯ | Resumed')
        else:
            await player.set_paused(True)
            await ctx.send(' ⏯ | Paused')

    @commands.command(aliases=['vol'])
    async def volume(self, ctx, volume=None):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        if not volume:
            return await ctx.send(f'🔈 | {player.volume}%')

        if not player.is_playing():
            return await ctx.send('Nothing playing.')

        if not ctx.author.voice or (player.is_connected() and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        if not lavalink.Utils.is_number(volume):
            return await ctx.send('You didn\'t specify a valid number!')

        v = await player.set_volume(int(volume))
        await ctx.send(f'🔈 | Set to {v}%')

    @commands.command()
    async def shuffle(self, ctx):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        if not player.is_playing():
            return await ctx.send('Nothing playing.')

        if not ctx.author.voice or (player.is_connected() and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        player.shuffle = not player.shuffle

        await ctx.send('🔀 | Shuffle ' + ('enabled' if player.shuffle else 'disabled'))

    @commands.command()
    async def repeat(self, ctx):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        if not player.is_playing():
            return await ctx.send('Nothing playing.')

        if not ctx.author.voice or (player.is_connected() and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        player.repeat = not player.repeat

        await ctx.send('🔁 | Repeat ' + ('enabled' if player.repeat else 'disabled'))

    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        if not ctx.author.voice or (player.is_connected() and ctx.author.voice.channel.id != int(player.channel_id)):
            return await ctx.send('You\'re not in my voicechannel!')

        await player.disconnect()


def setup(bot):
    bot.add_cog(Music(bot))


def teardown(bot):
    bot._lavaclient._destroy()
