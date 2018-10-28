import asyncio
import discord
from discord.ext import commands
from utils.equalizer import Equalizer


class Experimental:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def eq(self, ctx):
        player = self.bot.lavalink.players.get(ctx.guild.id)
        eq = player.fetch('eq', Equalizer())

        reactions = ['◀', '⬅', '⏫', '🔼', '🔽', '⏬', '➡', '▶', '⏺']

        veq = await ctx.send(f'```\n{eq.visualise()}```')
        for reaction in reactions:
            await veq.add_reaction(reaction)

        await self.interact(ctx, player, eq, veq, 0)

    async def interact(self, ctx, player, eq, m, selected):
        player.store('eq', eq)
        selector = f'{" " * 8}{"     " * selected}^^^'
        await m.edit(content=f'```\n{eq.visualise()}\n{selector}```')

        reaction = await self.get_reaction(ctx, m.id)

        if not reaction:
            try:
                await m.clear_reactions()
            except discord.Forbidden:
                pass
        elif reaction == '⬅':
            await self.interact(ctx, player, eq, m, max(selected - 1, 0))
        elif reaction == '➡':
            await self.interact(ctx, player, eq, m, min(selected + 1, 14))
        elif reaction == '🔼':
            gain = min(eq.get_gain(selected) + 0.1, 1.0)
            eq.set_gain(selected, gain)
            await self.apply_gain(ctx.guild.id, selected, gain)
            await self.interact(ctx, player, eq, m, selected)
        elif reaction == '🔽':
            gain = max(eq.get_gain(selected) - 0.1, -0.25)
            eq.set_gain(selected, gain)
            await self.apply_gain(ctx.guild.id, selected, gain)
            await self.interact(ctx, player, eq, m, selected)
        elif reaction == '⏫':
            gain = 1.0
            eq.set_gain(selected, gain)
            await self.apply_gain(ctx.guild.id, selected, gain)
            await self.interact(ctx, player, eq, m, selected)
        elif reaction == '⏬':
            gain = -0.25
            eq.set_gain(selected, gain)
            await self.apply_gain(ctx.guild.id, selected, gain)
            await self.interact(ctx, player, eq, m, selected)
        elif reaction == '◀':
            selected = 0
            await self.interact(ctx, player, eq, m, selected)
        elif reaction == '▶':
            selected = 14
            await self.interact(ctx, player, eq, m, selected)
        elif reaction == '⏺':
            for band in range(eq._band_count):
                eq.set_gain(band, 0.0)

            await self.apply_gains(ctx.guild.id, eq.bands)
            await self.interact(ctx, player, eq, m, selected)

    async def apply_gain(self, guild_id, band, gain):
        await self.apply_gains(guild_id, {'band': band, 'gain': gain})

    async def apply_gains(self, guild_id, gains):
        payload = {
            'op': 'equalizer',
            'guildId': str(guild_id)
        }

        if isinstance(gains, list):
            payload['bands'] = [{'band': x, 'gain': y} for x, y in enumerate(gains)]
        elif isinstance(gains, dict):
            payload['bands'] = [gains]

        await self.bot.lavalink.ws.send(**payload)

    async def get_reaction(self, ctx, m_id):
        reactions = ['◀', '⬅', '⏫', '🔼', '🔽', '⏬', '➡', '▶', '⏺']

        def check(r, u):
            return r.message.id == m_id and \
                    u.id == ctx.author.id and \
                    r.emoji in reactions

        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=20)
        except asyncio.TimeoutError:
            return None
        else:
            try:
                await reaction.message.remove_reaction(reaction.emoji, user)
            except discord.Forbidden:
                pass
            return reaction.emoji


def setup(bot):
    bot.add_cog(Experimental(bot))
