import asyncio
import json

import websockets

from . import PlayerManager


class _Lavalink:
    def __init__(self, bot):
        self.client = None
        self.players = PlayerManager(bot)
        self.ws = None


class Client:
    def __init__(self, bot, **kwargs):
        self.http = bot.http._session  # Let's use the bot's http session instead
        self.ws_tasks = []
        self.voice_state = {}
        self.hooks = {'track_start': [], 'track_end': []}

        self.bot = bot
        self.bot.add_listener(self.on_voice_state_update)
        self.bot.add_listener(self.on_voice_server_update)

        self.loop = kwargs.pop('loop', asyncio.get_event_loop())
        self.shard_count = self.bot.shard_count or kwargs.get("shard_count", 1)
        self.user_id = self.bot.user.id
        self.password = kwargs.pop('password', '')
        self.host = kwargs.pop('host', 'localhost')
        self.port = kwargs.pop('port', 80)
        self.rest = kwargs.pop('rest', 2333)
        self.uri = 'ws://{}:{}'.format(self.host, self.port)
        self.ws_retry = kwargs.pop('ws_retry', 3)

        if not hasattr(self.bot, 'lavalink'):
            self.bot.lavalink = _Lavalink(self.bot)
            self.loop.create_task(self._connect())
        
        if self.bot.lavalink.client is None:
            self.bot.lavalink.client = self
    
    async def register_listener(self, event, func):
        if event in self.hooks and func in self.hooks[event]:
            self.hooks[event].append(func)  
    
    async def unregister_listener(self, event, func):
        if event in self.hooks and func in self.hooks[event]:
            self.hooks[event].remove(func)

    async def _connect(self):
        try:
            headers = {
                'Authorization': self.password,
                'Num-Shards': self.shard_count,
                'User-Id': self.user_id
            }
            self.bot.lavalink.ws = await websockets.connect(self.uri, extra_headers=headers)
            self.loop.create_task(self._listen())
            print("[Lavalink.py] Established connection to lavalink")

            if len(self.ws_tasks) > 0:
                print("[Lavalink.py] Replaying {} WebSocket events...".format(len(self.ws_tasks)))
                for task in self.ws_tasks:
                    await self.send(**task)

        except OSError:
            print('[Lavalink.py] Failed to connect to lavalink')

    async def _listen(self):
        try:
            while self.bot.lavalink.ws.open:
                data = await self.bot.lavalink.ws.recv()
                j = json.loads(data)

                if 'op' in j:
                    if j.get('op') == 'validationReq':
                        await self._dispatch_join_validator(j)
                    elif j.get('op') == 'isConnectedReq':
                        await self._validate_shard(j)
                    elif j.get('op') == 'sendWS':
                        m = json.loads(j['message'])
                        await self.bot._connection._get_websocket(int(m['d'].get('guild_id', None))).send(j.get('message'))
                    elif j.get('op') == 'event':
                        await self._dispatch_event(j)
                    elif j.get('op') == 'playerUpdate':
                        await self._update_state(j)

        except websockets.ConnectionClosed:
            self.bot.lavalink.players.clear()

            print('[Lavalink.py] Connection closed... Attempting to reconnect in 30 seconds')
            self.bot.lavalink.ws.close()
            for a in range(0, self.ws_retry):
                await asyncio.sleep(30)
                print('[Lavalink.py] Attempting to reconnect (Attempt: {})'.format(a + 1))
                await self._connect()
                # if connection has been established, stop trying
                if self.bot.lavalink.ws.open:
                    return

            print('[Lavalink.py] Failed to re-establish a connection with lavalink.')

    async def _dispatch_event(self, data):
        t = data.get('type')
        g = int(data.get('guildId'))
        
        if self.bot.lavalink.players.has(g) and t == "TrackEndEvent":
            player = self.bot.lavalink.players[g]
            self.loop.create_task(player._on_track_end(data))

    async def _dispatch_join_validator(self, data):
        if self.bot.lavalink.players.has(int(data.get('guildId'))):
            p = self.bot.lavalink.players.get(int(data.get('guildId')))
            await p._validate_join(data)
        else:
            await self.send(op='validationRes', guildId=data.get('guildId'), channelId=data.get('channelId', None), valid=False)

    async def _update_state(self, data):
        g = int(data.get('guildId'))

        if self.bot.lavalink.players.has(int(data.get('guildId'))) and self.bot.lavalink.players.get(g).is_playing():
            p = self.bot.lavalink.players.get(g)

            p.position = data['state'].get('position', 0)
            p.position_timestamp = data['state'].get('time', 0)

    async def _update_voice(self, guild_id, channel_id):
        if self.bot.lavalink.players.has(guild_id):
            p = self.bot.lavalink.players.get(guild_id)
            p.channel_id = None if not channel_id else str(channel_id)

    async def _validate_shard(self, data):
        await self.send(op='isConnectedRes', shardId=data.get('shardId'), connected=True)

    async def send(self, **data):
        if not self.bot.lavalink.ws or not self.bot.lavalink.ws.open:
            self.ws_tasks.append(data)
        else:
            await self.bot.lavalink.ws.send(json.dumps(data))

    async def get_tracks(self, query):
        data = await self.http.get('http://{}:{}/loadtracks?identifier={}'.format(self.host, self.rest, query),
                                   headers={'Authorization': self.password, 'Accept': 'application/json'})
        return await data.json(content_type=None)

    # Bot Events
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.user_id:
            await self._update_voice(guild_id=member.guild.id, channel_id=after.channel.id if after.channel else None)

            self.voice_state.update({'sessionId': after.session_id})
            await self.verify_and_dispatch()

    async def on_voice_server_update(self, data):
        self.voice_state.update({
            'op': 'voiceUpdate',
            'guildId': data.get('guild_id'),
            'event': data
        })

        await self.verify_and_dispatch()

    async def verify_and_dispatch(self):
        if {'op', 'guildId', 'sessionId', 'event'} == self.voice_state.keys():
            await self.send(**self.voice_state)
            self.voice_state.clear()

    def _destroy(self):
        self.bot.remove_listener(self.on_voice_state_update)
        self.bot.remove_listener(self.on_voice_server_update)

        for h in self.hooks.values():
            h.clear()

        self.bot.lavalink.client = None
