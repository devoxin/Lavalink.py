import asyncio
import json
from datetime import datetime

from . import PlayerManager, WebSocket


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
            p.position_timestamp(data['state']['time'])

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
        print('[{}] [{}] {}'.format(datetime.utcnow().strftime('%H:%M:%S'), level, content))
