import asyncio
import json

import aiohttp
import websockets


class Requests:
    def __init__(self):
        self.pool = aiohttp.ClientSession()

    async def get(self, url, jsonify=False, *args, **kwargs):
        try:
            async with self.pool.get(url, *args, **kwargs) as r:
                if r.status != 200:
                    return None

                if jsonify:
                    return await r.json(content_type=None)

                return await r.read()
        except (aiohttp.ClientOSError, aiohttp.ClientConnectorError, asyncio.TimeoutError):
            return None


class AudioTrack:
    def __init__(self, track, identifier, can_seek, author, duration, stream, title, uri, requester):
        self.track = track
        self.identifier = identifier
        self.can_seek = can_seek
        self.author = author
        self.duration = duration
        self.stream = stream
        self.title = title
        self.uri = uri
        self.requester = requester


class Player:
    def __init__(self, client, guild_id):
        self.client = client
        self.shard_id = client.bot.get_guild(guild_id).shard_id
        self.guild_id = str(guild_id)
        self.channel_id = None

        self.is_connected = lambda: self.channel_id is not None
        self.is_playing = lambda: self.current is not None

        self.position = 0
        self.position_timestamp = 0

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
    
    async def disconnect(self):
        if not self.is_connected():
            return

        if self.is_playing():
            await self.stop()

        payload = {
            'op': 'disconnect',
            'guildId': self.guild_id
        }
        await self.client.send(payload)
        self.channel_id = None

    async def add(self, requester, track, play=False):
        await self._build_track(requester, track)

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
        self.position = 0
        if data.get('reason') == 'FINISHED':
            await self.play()

    async def _build_track(self, requester, track):
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
            i = requester
            t = AudioTrack(a, b, c, d, e, f, g, h, i)
            self.queue.append(t)
        except KeyError:
            return  # Raise invalid track passed

    async def _validate_join(self, data):
        payload = {
            'op': 'validationRes',
            'guildId': data.get('guildId'),
            'channelId': data.get('channelId', None),
            'valid': True
        }
        await self.client.send(payload)


class Client:
    def __init__(self, bot, password='', host='localhost', port=80, rest=2333, loop=asyncio.get_event_loop()):
        self.bot = bot

        if not hasattr(self.bot, 'players'):
            self.bot.players = {}

        self.loop = loop
        self.shard_count = len(self.bot.shards) if hasattr(self.bot, 'shards') else 1
        self.user_id = self.bot.user.id
        self.password = password
        self.host = host
        self.port = port
        self.rest = rest
        self.uri = f'ws://{host}:{port}'
        self.requester = Requests()

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
                    await self.bot._connection._get_websocket(330777295952543744).send(j.get('message'))  # todo: move this to play (voice updates)
                elif j.get('op') == 'event':
                    await self._dispatch_event(j)
                elif j.get('op') == 'playerUpdate':
                    await self._update_state(j)

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

    async def _update_state(self, data):
        g = int(data.get('guildId'))

        if g not in self.bot.players:
            return

        p = self.bot.players[g]

        if not p.is_playing():
            return

        p.position = data['state'].get('position', 0)
        p.position_timestamp = data['state'].get('time', 0)

    async def _validate_shard(self, data):
        payload = {
            'op': 'isConnectedRes',
            'shardId': data.get('shardId'),
            'connected': True
        }
        await self.send(payload)

    async def send(self, data):
        if not hasattr(self, 'ws') or not self.ws.open:
            return
        payload = json.dumps(data)
        await self.ws.send(payload)

    async def dispatch_voice_update(self, payload):
        await self.send(payload)

    async def get_player(self, guild_id):
        if guild_id not in self.bot.players:
            p = Player(client=self, guild_id=guild_id)
            self.bot.players[guild_id] = p

        return self.bot.players[guild_id]

    async def get_tracks(self, query):
        headers = {
            'Authorization': self.password,
            'Accept': 'application/json'
        }
        return await self.requester.get(url=f'http://{self.host}:{self.rest}/loadtracks?identifier={query}', jsonify=True, headers=headers)
        # data = {
        #     'is_search': any(s in query for s in ['ytsearch', 'scsearch']),
        #     'results': tracks
        # }
        # return data

class Utils:

    @staticmethod
    def format_time(time):
        seconds = (time / 1000) % 60
        minutes = (time / (1000 * 60)) % 60
        hours = (time / (1000 * 60 * 60)) % 24
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
