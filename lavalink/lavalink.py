import asyncio
import json
from random import randrange

import aiohttp
import websockets

__version__ = '1.0.1'


class InvalidTrack(Exception):
    def __init__(self, message):
        super().__init__(message)


class IGeneric:
    def __init__(self):
        self.requester = None
        self.ws = None


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
    async def build(self, track, requester):
        try:
            self.track = track['track']
            self.identifier = track['info']['identifier']
            self.can_seek = track['info']['isSeekable']
            self.author = track['info']['author']
            self.duration = track['info']['length']
            self.stream = track['info']['isStream']
            self.title = track['info']['title']
            self.uri = track['info']['uri']
            self.requester = requester

            return self
        except KeyError:
            raise InvalidTrack('an invalid track was passed')


class Player:
    def __init__(self, client, guild_id):
        self.client = client
        self.shard_id = client.bot.get_guild(guild_id).shard_id
        self.guild_id = str(guild_id)
        self.channel_id = None

        self.is_connected = lambda: self.channel_id is not None
        self.is_playing = lambda: self.channel_id is not None and self.current is not None
        self.paused = False

        self.position = 0
        self.position_timestamp = 0
        self.volume = 100

        self.queue = []
        self.current = None

        self.shuffle = False
        self.repeat = False

    async def connect(self, channel_id):
        await self.client.send(op='connect', guildId=self.guild_id, channelId=str(channel_id))

    async def disconnect(self):
        if not self.is_connected():
            return

        if self.is_playing():
            await self.stop()

        await self.client.send(op='disconnect', guildId=self.guild_id)

    async def add(self, requester, track, play=False):
        self.queue.append(await AudioTrack().build(track, requester))

        if play and not self.is_playing():
            await self.play()

    async def play(self):
        if not self.is_connected() or not self.queue:
            if self.is_playing():
                await self.stop()

            self.current = None
            return

        if self.shuffle:
            track = self.queue.pop(randrange(len(self.queue)))
        else:
            track = self.queue.pop(0)

        await self.client.send(op='play', guildId=self.guild_id, track=track.track)
        self.current = track

    async def stop(self):
        await self.client.send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        await self.play()

    async def set_paused(self, pause):
        await self.client.send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol):
        if not Utils.is_number(vol):
            return

        if vol < 0:
            vol = 0

        if vol > 150:
            vol = 150

        await self.client.send(op='volume', guildId=self.guild_id, volume=vol)
        self.volume = vol
        return vol

    async def seek(self, pos):
        await self.client.send(op='seek', guildId=self.guild_id, position=pos)

    async def _on_track_end(self, data):
        self.position = 0
        self.paused = False

        if data.get('reason') == 'FINISHED':
            await self.play()

    async def _validate_join(self, data):
        await self.client.send(op='validationRes', guildId=data.get('guildId'), channelId=data.get('channelId', None), valid=True)


class Client:
    def __init__(self, bot, shard_count=1, password='', host='localhost', port=80, rest=2333, ws_retry=3, loop=asyncio.get_event_loop()):
        self.bot = bot

        self.loop = loop
        self.shard_count = self.bot.shard_count or shard_count
        self.user_id = self.bot.user.id
        self.password = password
        self.host = host
        self.port = port
        self.rest = rest
        self.uri = f'ws://{host}:{port}'
        self.ws_retry = ws_retry

        if not hasattr(self.bot, 'players'):
            self.bot.players = {}

        if not hasattr(self.bot, 'lavalink'):
            self.bot.lavalink = IGeneric()
            self.bot.lavalink.requester = Requests()
            asyncio.ensure_future(self._connect())

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
            while True:
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
                print(f'[Lavalink.py] Attempting to reconnect (Attempt: {a + 1})')
                await self._connect()
                if self.bot.lavalink.ws.open:
                    return

            print('[Lavalink.py] Failed to re-establish a connection with lavalink.')

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
            await self.send(op='validationRes', guildId=data.get('guildId'), channelId=data.get('channelId', None), valid=False)

    async def _update_state(self, data):
        g = int(data.get('guildId'))

        if g not in self.bot.players or not self.bot.players[g].is_playing():
            return

        p = self.bot.players[g]

        p.position = data['state'].get('position', 0)
        p.position_timestamp = data['state'].get('time', 0)
    
    async def _update_voice(self, guild_id, channel_id):
        if guild_id not in self.bot.players:
            return
        
        p = self.bot.players[guild_id]
        p.channel_id = None if not channel_id else str(channel_id)

    async def _validate_shard(self, data):
        await self.send(op='isConnectedRes', shardId=data.get('shardId'), connected=True)

    async def send(self, **data):
        if not self.bot.lavalink.ws or not self.bot.lavalink.ws.open:
            return

        await self.bot.lavalink.ws.send(json.dumps(data))

    async def get_player(self, guild_id):
        if guild_id not in self.bot.players:
            p = Player(client=self, guild_id=guild_id)
            self.bot.players[guild_id] = p

        return self.bot.players[guild_id]

    async def get_playing(self):
        return len([p for p in self.bot.players.values() if p.is_playing()])

    async def get_tracks(self, query):
        headers = {
            'Authorization': self.password,
            'Accept': 'application/json'
        }
        return await self.bot.lavalink.requester.get(url=f'http://{self.host}:{self.rest}/loadtracks?identifier={query}', jsonify=True, headers=headers)


class Utils:

    @staticmethod
    def format_time(time):
        seconds = (time / 1000) % 60
        minutes = (time / (1000 * 60)) % 60
        hours = (time / (1000 * 60 * 60)) % 24
        return "%02d:%02d:%02d" % (hours, minutes, seconds)

    @staticmethod
    def is_number(num):
        if num is None:
            return False

        try:
            int(num)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_number(num, default=1):
        if num is None:
            return default

        try:
            return int(num)
        except ValueError:
            return default
