import asyncio
import json

import discord
from . import webreq
import websockets

class AudioTrack:
    def __init__(self, track, identifier, can_seek, author, duration, stream, title, uri):
        self.track = track
        self.identifier = identifier
        self.can_seek = can_seek
        self.author = author
        self.duration = duration
        self.stream = stream
        self.title = title
        self.uri = uri

class Player:
    def __init__(self, client, guild_id, shard_id):
        self.client = client
        self.shard_id = shard_id
        self.guild_id = str(guild_id)
        self.channel_id = None

        self.is_connected = lambda: self.channel_id is not None
        self.is_playing = lambda: self.current is not None

        self.state = None
        
        self.queue = []
        self.current = None

    async def connect(self, channel_id):
        payload = {
            'op': 'connect',
            'guildId': self.guild_id,
            'channelId': str(channel_id)
        }
        await self.client.send(payload)
        self.channel_id = str(channel_id)

    async def add(self, track, play=False):
        await self._build_track(track)

        if play and not self.is_playing():
            await self.play()

    async def play(self):
        if not self.is_connected() or not self.queue:
            if self.is_playing():
                await self.stop()
            
            self.current = None
            return

        track = self.queue.pop(0)

        payload = {
            'op': 'play',
            'guildId': self.guild_id,
            'track': track.track
        }
        await self.client.send(payload)
        self.current = track
    
    async def stop(self):
        payload = {
            'op': 'stop',
            'guildId': self.guild_id
        }
        await self.client.send(payload)
        self.current = None
    
    async def skip(self):
        await self.play()
        
    async def _on_track_end(self, data):
        if data.get('reason') == 'FINISHED':
            await self.play()

    async def _build_track(self, track):
        try:
            a = track.get('track')
            info = track.get('info')
            b = info.get('identifier')
            c = info.get('isSeekable')
            d = info.get('author')
            e = info.get('length')
            f = info.get('isStream')
            g = info.get('title')
            h = info.get('uri')
            t = AudioTrack(a, b, c, d, e, f, g, h)
            self.queue.append(t)
        except KeyError:
            return # Raise invalid track passed

    async def _validate_join(self, data):
        payload = {
            'op': 'validationRes',
            'guildId': data.get('guildId'),
            'channelId': data.get('channelId', None),
            'valid': True
        }
        await self.client.send(payload)


class Client:
    def __init__(self, bot, shard_count, user_id, password='', host='localhost', port=80, loop=asyncio.get_event_loop()):
        self.bot = bot

        if not hasattr(self.bot, 'players'):
            self.bot.players = {}

        self.loop = loop
        self.shard_count = shard_count
        self.user_id = user_id
        self.password = password
        self.host = host
        self.port = port
        self.uri = f'ws://{host}:{port}'

        loop.create_task(self._connect())
    
    async def _connect(self):
        headers = {
            'Authorization': self.password,
            'Num-Shards': self.shard_count,
            'User-Id': self.user_id
        }
        try:
            self.ws = await websockets.connect(self.uri, extra_headers=headers)
            self.loop.create_task(self._listen())
            print("[WS] Ready")
        except Exception as e:
            raise e from None
    
    async def _listen(self):
        while True:
            data = await self.ws.recv()
            j = json.loads(data)

            if 'op' in j:
                if j.get('op') == 'validationReq':
                    await self._dispatch_join_validator(j)
                elif j.get('op') == 'isConnectedReq':
                    await self._validate_shard(j)
                elif j.get('op') == 'sendWS':
                    await self.bot._connection._get_websocket(330777295952543744).send(j.get('message')) # todo: move this to play (voice updates)
                elif j.get('op') == 'event':
                    await self._dispatch_event(j)
                #elif j.get('op') == 'playerUpdate':                
    
    async def _dispatch_event(self, data):
        t = data.get('type')
        g = int(data.get('guildId'))
        
        if g not in self.bot.players:
            return

        if t == 'TrackEndEvent':
            player = self.bot.players[g]
            asyncio.ensure_future(player._on_track_end(data))

    async def _dispatch_join_validator(self, data):
        if int(data.get('guildId')) in self.bot.players:
            p = self.bot.players[int(data.get('guildId'))]
            await p._validate_join(data)
        else:
            payload = {
                'op': 'validationRes',
                'guildId': data.get('guildId'),
                'channelId': data.get('channelId', None),
                'valid': False
            }
            await self.send(payload)

    async def _validate_shard(self, data):
        payload = {
            'op': 'isConnectedRes',
            'shardId': data.get('shardId'),
            'connected': True
        }
        await self.send(payload)

    async def send(self, data):
        if not self.ws:
            return
        payload = json.dumps(data)
        await self.ws.send(payload)
    
    async def dispatch_voice_update(self, payload):
        await self.send(payload)

    async def get_player(self, guild_id, shard_id):
        if guild_id not in self.bot.players:
            p = Player(client=self, guild_id=guild_id, shard_id=shard_id)
            self.bot.players[guild_id] = p

        return self.bot.players[guild_id]

    async def get_tracks(self, query):
        headers = {
            'Authorization': self.password,
            'Accept': 'application/json'
        }
        return await webreq.get(f'http://{self.host}:2333/loadtracks?identifier={query}', jsonify=True, headers=headers)
