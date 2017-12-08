import asyncio

from discord.ext import commands
from utils import lavalink


def arg(a, b, ignore_case=False):
    if ignore_case:
        return a.lower() == b.lower()
    else:
        return a == b


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.lavalink = lavalink.Client(bot=bot, shard_count=len(self.bot.shards), user_id=self.bot.user.id, password='youshallnotpass', loop=self.bot.loop)

        self.state_keys = {}
        self.validator = ['op', 'guildId', 'sessionId', 'event']
        #self.voice = getattr(self.bot, '_vsu', None)
        #self.bot.loop.create_task(self.monitor_vsu())

    # @commands.command()
    # async def test(self, ctx, a: lambda c: arg(c, 'test', True) = False):
    #     print(a)

    @commands.command()
    async def play(self, ctx, *, query):
        tracks = await self.lavalink.get_tracks(f'ytsearch:{query}')
        await self.lavalink.send_connect_request(ctx)
        await self.lavalink.play_track(ctx, tracks[0])
    
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
