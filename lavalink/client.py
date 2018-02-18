from datetime import datetime

from .utils import LogLevel
from .audio_events import TrackEndEvent, TrackExceptionEvent, TrackStuckEvent
from .players import *
from .web_socket import *


class Lavalink:
    def __init__(self, bot):
        self.client = None
        self.players = PlayerManager(bot)
        self.ws = None


class Client:
    def __init__(self, bot, **kwargs):
        self.http = bot.http._session  # Let's use the bot's http session instead
        self.voice_state = {}
        self.log_level = kwargs.pop('log_level', LogLevel.debug).value

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

    async def trigger_event(self, data):
        g = int(data['guildId'])
        event_name = data['type']
        player = self.bot.lavalink.players[g]
        track = player.current  # Dunno how to decode the base64 encoded track item

        if player:
            event = None
            if event_name == 'TrackEndEvent':
                event = TrackEndEvent(player, track, data['reason'])
            elif event_name == 'TrackExceptionEvent':
                event = TrackExceptionEvent(player, track, data['error'])
            elif event_name == 'TrackStuckEvent':
                event = TrackStuckEvent(player, track, data['thresholdMs'])
            if event:
                await player.trigger_event(event)

    async def update_state(self, data):
        g = int(data['guildId'])

        if self.bot.lavalink.players.has(g):
            p = self.bot.lavalink.players.get(g)
            p._position = data['state']['position']
            p._position_timestamp = data['state']['time']

    async def get_tracks(self, query):
        self.log('debug', 'Requesting tracks for query ' + query)
        async with self.http.get(self.rest_uri + query, headers={'Authorization': self.password}) as res:
            js = await res.json(content_type=None)
            res.close()
            return js

    # Bot Events
    async def on_socket_response(self, data):
        # INTERCEPT VOICE UPDATES
        if not data or data.get('t', '') not in ['VOICE_STATE_UPDATE', 'VOICE_SERVER_UPDATE']:
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

    def destroy(self):
        self.bot.remove_listener(self.on_socket_response)
        self.bot.lavalink.client = None

    def log(self, level, content):
        lvl = LogLevel[level].value
        if lvl >= self.log_level:
            print('[{}] [lavalink.py] [{}] {}'.format(datetime.utcnow().strftime('%H:%M:%S'), level, content))
