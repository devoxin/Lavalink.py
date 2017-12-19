import asyncio
import json

import websockets
from models import Player
from utils import IGeneric, Requests


class Client:
    def __init__(self, bot, shard_count=1, password='', host='localhost', port=80, rest=2333, ws_retry=3, loop=asyncio.get_event_loop()):
        self.bot = bot
        bot._lavaclient = self

        self.hooks = {'track_start': [], 'track_end': []}
        self.validator = ['op', 'guildId', 'sessionId', 'event']
        self.voice_state = {}
        self.bot.add_listener(self.on_voice_state_update)
        self.bot.add_listener(self.on_voice_server_update)

        self.loop = loop
        self.shard_count = self.bot.shard_count or shard_count
        self.user_id = self.bot.user.id
        self.password = password
        self.host = host
        self.port = port
        self.rest = rest
        self.uri = 'ws://{}:{}'.format(host, port)
        self.ws_retry = ws_retry

        if not hasattr(self.bot, 'players'):
            self.bot.players = {}

        if not hasattr(self.bot, 'lavalink'):
            self.bot.lavalink = IGeneric()
            self.bot.lavalink.requester = Requests()
            asyncio.ensure_future(self._connect())
    
    async def register_listener(self, event, func):
        if event in self.hooks and func in self.hooks[event]:
            self.hooks[event].append(func)  
    
    async def unregister_listener(self, event, func):
        if event in self.hooks and func in self.hooks[event]:
            self.hooks[event].remove(func)
    
    def unregister_listeners(self):
        for h in hooks.values():
            h.clear()

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
            for p in self.bot.players.values():
                p.channel_id = None
                p.current = None

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
        
        if g in self.bot.players and t == "TrackEndEvent":
            player = self.bot.players[g]
            asyncio.ensure_future(player._on_track_end(data))

    async def _dispatch_join_validator(self, data):
        if int(data.get('guildId')) in self.bot.players:
            p = self.bot.players[int(data.get('guildId'))]
            await p._validate_join(data)
        else:
            await self.send(op='validationRes', guildId=data.get('guildId'), channelId=data.get('channelId', None), valid=False)

    async def _update_state(self, data):
        g = int(data.get('guildId'))

        if g in self.bot.players and self.bot.players[g].is_playing():
            p = self.bot.players[g]

            p.position = data['state'].get('position', 0)
            p.position_timestamp = data['state'].get('time', 0)

    async def _update_voice(self, guild_id, channel_id):
        if guild_id in self.bot.players:
            p = self.bot.players[guild_id]
            p.channel_id = None if not channel_id else str(channel_id)

    async def _validate_shard(self, data):
        await self.send(op='isConnectedRes',
                        shardId=data.get('shardId'),
                        connected=True)

    async def send(self, **data):
        if self.bot.lavalink.ws and self.bot.lavalink.ws.open:
            await self.bot.lavalink.ws.send(json.dumps(data))

    async def get_tracks(self, query):
        headers = {
            'Authorization': self.password,
            'Accept': 'application/json'
        }
        return await self.bot.lavalink.requester.get(url='http://{}:{}/loadtracks?identifier={}'.format(self.host, self.rest, query),
                                                     jsonify=True, headers=headers)

    # Bot Events
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id:
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
        if all(k in self.voice_state for k in self.validator):
            await self.send(**self.voice_state)
            self.voice_state.clear()

    def _destroy(self):
        self.bot.remove_listener(self.on_voice_state_update)
        self.bot.remove_listener(self.on_voice_server_update)
        self.unregister_listeners()
        del(self.bot._lavaclient)
