import asyncio
import json
from datetime import datetime
from random import randrange

import websockets


def resolve_log_level(level):
    if level == 'verbose':
        return 0
    elif level == 'debug':
        return 1
    elif level == 'info':
        return 2
    elif level == 'warn':
        return 3
    elif level == 'error':
        return 4
    else:
        return 0


class Lavalink:
    def __init__(self, bot):
        self.client = None
        self.players = PlayerManager(bot)
        self.ws = None


class Client:
    def __init__(self, bot, **kwargs):
        self.http = bot.http._session  # Let's use the bot's http session instead
        self.voice_state = {}
        self.hooks = {'track_start': [], 'track_end': []}
        self.log_level = resolve_log_level(kwargs.pop('log_level', 'info'))

        self.bot = bot
        self.bot.add_listener(self.on_socket_response)

        self.loop = kwargs.pop('loop', asyncio.get_event_loop())
        self.user_id = self.bot.user.id
        self.rest_uri = 'http://{}:{}/loadtracks?identifier='.format(kwargs.get('host', 'localhost'), kwargs.pop('rest', 2333))
        self.password = kwargs.get('password', '')

        if not hasattr(self.bot, 'lavalink'):
            self.bot.lavalink = Lavalink(self.bot)
            self.bot.lavalink.ws = WebSocket(self, **kwargs)

        if not self.bot.lavalink.client:
            self.bot.lavalink.client = self

    async def register_listener(self, event, func):
        if event in self.hooks and func in self.hooks[event]:
            self.hooks[event].append(func)

    async def unregister_listener(self, event, func):
        if event in self.hooks and func in self.hooks[event]:
            self.hooks[event].remove(func)

    async def _dispatch_event(self, data):
        t = data.get('type')
        g = int(data.get('guildId'))

        if self.bot.lavalink.players.has(g) and t == "TrackEndEvent":
            player = self.bot.lavalink.players.get(g)
            await player.on_track_end(data)

    async def _update_state(self, data):
        g = int(data['guildId'])

        if self.bot.lavalink.players.has(g):
            p = self.bot.lavalink.players.get(g)
            p.position = data['state']['position']
            p.position_timestamp = data['state']['time']

    async def get_tracks(self, query):
        async with self.http.get(self.rest_uri + query,
                                 headers={'Authorization': self.password, 'Accept': 'application/json'}) as res:
            return await res.json(content_type=None)

    # Bot Events
    async def on_socket_response(self, data):
        # INTERCEPT VOICE UPDATES
        if not data or data['op'] != 0 or not data['t'] or data['t'] not in ['VOICE_STATE_UPDATE', 'VOICE_SERVER_UPDATE']:
            return

        if data['t'] == 'VOICE_SERVER_UPDATE':
            self.voice_state.update({
                'op': 'voiceUpdate',
                'guildId': data['d']['guild_id'],
                'event': data['d']
            })
        else:
            if int(data['d']['user_id']) != self.bot.user.id:
                return
            self.voice_state.update({
                'sessionId': data['d']['session_id']
            })

        if {'op', 'guildId', 'sessionId', 'event'} == self.voice_state.keys():
            await self.bot.lavalink.ws.send(**self.voice_state)
            self.voice_state.clear()

    def _destroy(self):
        self.bot.remove_listener(self.on_voice_state_update)
        self.bot.remove_listener(self.on_voice_server_update)

        for h in self.hooks.values():
            h.clear()

        self.bot.lavalink.client = None

    def log(self, level, content):
        lvl = resolve_log_level(level)
        if lvl >= self.log_level:
            print('[{}] [{}] {}'.format(datetime.utcnow().strftime('%H:%M:%S'), level, content))


class WebSocket:
    def __init__(self, lavalink, **kwargs):
        self._lavalink = lavalink
        self.log = self._lavalink.log

        self._ws = None
        self._queue = []

        self._ws_retry = kwargs.pop('ws_retry', 3)
        self._password = kwargs.get('password', '')
        self._host = kwargs.get('host', 'localhost')
        self._port = kwargs.pop('port', 80)
        self._uri = 'ws://{}:{}'.format(self._host, self._port)
        self._shards = self._lavalink.bot.shard_count or kwargs.pop("shard_count", 1)
        self._user_id = self._lavalink.bot.user.id

        self._loop = self._lavalink.bot.loop
        self._loop.create_task(self.connect())

    async def connect(self):
        """ Establishes a connection to the Lavalink server """
        await self._lavalink.bot.wait_until_ready()

        if self._ws and self._ws.open:
            self.log('debug', 'Websocket still open, closing...')
            self._ws.close()

        headers = {
            'Authorization': self._password,
            'Num-Shards': self._shards,
            'User-Id': self._user_id
        }
        self.log('verbose', 'Preparing to connect to Lavalink')
        self.log('verbose', '    with URI: {}'.format(self._uri))
        self.log('verbose', '    with headers: {}'.format(str(headers)))
        self.log('info', 'Connecting to Lavalink...')

        try:
            self._ws = await websockets.connect(self._uri, extra_headers=headers)
        except OSError:
            self.log('info', 'Failed to connect to Lavalink. ')
        else:
            self.log('info', 'Connected to Lavalink!')
            self._loop.create_task(self.listen())
            if self._queue:
                self.log('info', 'Replaying {} queued events...'.format(len(self._queue)))
                for task in self._queue:
                    await self.send(**task)

    async def listen(self):
        try:
            while self._ws.open:
                data = json.loads(await self._ws.recv())
                op = data.get('op', None)
                self.log('verbose', 'Received websocket data\n' + str(data))

                if not op:
                    return self.log('debug', 'Received websocket message without op\n' + str(data))

                if op == 'event':
                    await self._lavalink._dispatch_event(data)
                elif op == 'playerUpdate':
                    await self._lavalink._update_state(data)
        except websockets.ConnectionClosed:
            self.bot.lavalink.players.clear()

            self.log('warn', 'Connection closed; attempting to reconnect in 30 seconds')
            self._ws.close()
            for a in range(0, self._ws_retry):
                await asyncio.sleep(30)
                self.log('info', 'Reconnecting... (Attempt {})'.format(a + 1))
                await self.connect()

                if self._ws.open:
                    return

            self.log('warn', 'Unable to reconnect to Lavalink!')

    async def send(self, **data):
        if not self._ws or not self._ws:
            self._queue.append(data)
            self.log('verbose', 'Websocket not ready; appending payload to queue\n' + str(data))
        else:
            self.log('verbose', 'Sending payload:\n' + str(data))
            await self._ws.send(json.dumps(data))


class InvalidTrack(Exception):
    def __init__(self, message):
        super().__init__(message)


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


class PlayerManager:
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def __len__(self):
        return len(self.players)

    def __getitem__(self, item):
        return self.players.get(item, None)

    def __contains__(self, item):
        return item in self.players

    def find(self, predicate):
        found = list(filter(predicate, self.players))
        return found[0] if found else None

    def find_all(self, predicate):
        return list(filter(predicate, self.players))

    def get(self, guild_id):
        if guild_id not in self.players:
            p = Player(bot=self.bot, guild_id=guild_id)
            self.players[guild_id] = p

        return self.players[guild_id]

    def has(self, guild_id):
        return guild_id in self.players

    def clear(self):
        self.players.clear()

    def get_playing(self):
        return len([p for p in self.players.values() if p.is_playing()])


class Player:
    def __init__(self, bot, guild_id: int):
        self.bot = bot

        self.shard_id = bot.get_guild(guild_id).shard_id
        self.guild_id = str(guild_id)

        self.is_playing = lambda: self.current is not None
        self.paused = False

        self.position = 0
        self.position_timestamp = 0
        self.volume = 100

        self.queue = []
        self.current = None

        self.shuffle = False
        self.repeat = False

    @property
    def connected_channel(self):
        g = self.bot.get_guild(int(self.guild_id))
        if not g or not g.voice_client:
            return None
        return g.voice_client.channel

    async def add(self, requester, track, play=False):
        self.queue.append(await AudioTrack().build(track, requester))

        if play and not self.is_playing():
            await self.play()

    async def play(self):
        if self.current is not None or not self.queue:
            return

        if self.shuffle:
            track = self.queue.pop(randrange(len(self.queue)))
        else:
            track = self.queue.pop(0)

        await self.bot.lavalink.ws.send(op='play', guildId=self.guild_id, track=track.track)
        self.current = track

    async def stop(self):
        await self.bot.lavalink.ws.send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        await self.play()

    async def set_paused(self, pause: bool):
        await self.bot.lavalink.ws.send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        if isinstance(vol, int):
            self.volume = max(min(vol, 150), 0)

            await self.bot.lavalink.ws.send(op='volume', guildId=self.guild_id, volume=self.volume)
            return self.volume

    async def seek(self, pos: int):
        await self.bot.lavalink.ws.send(op='seek', guildId=self.guild_id, position=pos)

    async def on_track_end(self, data):
        self.position = 0
        self.paused = False
        self.current = None

        if data.get('reason') == 'FINISHED':
            await self.play()


class Utils:

    @staticmethod
    def format_time(time):
        seconds = (time / 1000) % 60
        minutes = (time / (1000 * 60)) % 60
        hours = (time / (1000 * 60 * 60)) % 24
        return "%02d:%02d:%02d" % (hours, minutes, seconds)

    @staticmethod
    def get_number(num, default=1):
        if num is None:
            return default

        try:
            return int(num)
        except ValueError:
            return default
