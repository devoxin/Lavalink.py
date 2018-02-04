import math
import re

import discord
from discord.ext import commands
from utils import lavalink

time_rx = re.compile('[0-9]+')


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.lavalink = lavalink.Client(bot=bot, password='youshallnotpass', loop=self.bot.loop, log_level='verbose')
        self.lavalink.register_listener('track_end', self.track_end)
        # As of 2.0, lavalink.Client will be available via self.bot.lavalink.client

    async def track_end(self, player):
        if int(player.guild_id) == 330777295952543744:
            await self.bot.get_channel(353911657665396736).send('[event hook test] track ended')

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, query):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_connected:
            if ctx.author.voice is None or ctx.author.voice.channel is None:
                return await ctx.send('Join a voice channel!')
            await ctx.author.voice.channel.connect(reconnect=False)
        else:
            if ctx.author.voice is None or ctx.author.voice.channel is None or player.connected_channel.id != ctx.author.voice.channel.id:
                return await ctx.send('Join my voice channel!')

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

    @commands.command()
    async def seek(self, ctx, time):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Not playing.')

        pos = '+'
        if time.startswith('-'):
            pos = '-'

        seconds = time_rx.search(time)

        if not seconds:
            return await ctx.send('You need to specify the amount of seconds to skip!')

        seconds = int(seconds.group()) * 1000

        if pos == '-':
            seconds = seconds * -1
        
        track_time = player.position + seconds

        await player.seek(track_time)

        await ctx.send(f'Moved track to **{lavalink.Utils.format_time(track_time)}**')

    @commands.command(aliases=['forceskip', 'fs'])
    async def skip(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Not playing.')

        await player.skip()
        await ctx.send('⏭ | Skipped.')

    @commands.command(aliases=['np', 'n'])
    async def now(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
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
        player = self.bot.lavalink.players.get(ctx.guild.id)

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
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Not playing.')

        if player.paused:
            await player.set_paused(False)
            await ctx.send('⏯ | Resumed')
        else:
            await player.set_paused(True)
            await ctx.send(' ⏯ | Paused')

    @commands.command(aliases=['vol'])
    async def volume(self, ctx, volume: int=None):
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not volume:
            return await ctx.send(f'🔈 | {player.volume}%')

        v = await player.set_volume(volume)
        await ctx.send(f'🔈 | Set to {v}%')

    @commands.command()
    async def shuffle(self, ctx):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Nothing playing.')

        player.shuffle = not player.shuffle

        await ctx.send('🔀 | Shuffle ' + ('enabled' if player.shuffle else 'disabled'))

    @commands.command()
    async def repeat(self, ctx):
        player = self.bot.lavalink.players.get(guild_id=ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('Nothing playing.')

        player.repeat = not player.repeat

        await ctx.send('🔁 | Repeat ' + ('enabled' if player.repeat else 'disabled'))

    @commands.is_owner()
    @commands.command(aliases=['dc'])
    async def disconnect(self, ctx):  # Don't use this, it's incredibly prone to fucking up your bot
        player = self.bot.lavalink.players.get(ctx.guild.id)

        if not player.is_connected:
            return await ctx.send('Not connected.')

        await player.disconnect()


def setup(bot):
    bot.add_cog(Music(bot))


def teardown(bot):
    bot._lavaclient._destroy()
