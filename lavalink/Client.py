import asyncio
import logging
import aiohttp

from .PlayerManager import PlayerManager, DefaultPlayer
from .WebSocket import WebSocket
from .Events import TrackStuckEvent, TrackExceptionEvent, TrackEndEvent


log = logging.getLogger(__name__)


def set_log_level(log_level):
    root_log = logging.getLogger(__name__.split('.')[0])
    root_log.setLevel(log_level)


class Client:
    def __init__(self, bot, log_level=logging.INFO, loop=asyncio.get_event_loop(), host='localhost',
                 rest_port=2333, password='', ws_retry=3, ws_port=80, shard_count=1, player=DefaultPlayer):

        bot.lavalink = self
        self.http = aiohttp.ClientSession(loop=loop)
        self.voice_state = {}
        self.hooks = []

        set_log_level(log_level)

        self.bot = bot
        self.bot.add_listener(self.on_socket_response)

        self.loop = loop
        self.rest_uri = 'http://{}:{}/loadtracks?identifier='.format(host, rest_port)
        self.password = password

        self.ws = WebSocket(
            self, host, password, ws_port, ws_retry, shard_count
        )
        self.players = PlayerManager(self, player)

    def register_hook(self, func):
        if func not in self.hooks:
            self.hooks.append(func)

    def unregister_hook(self, func):
        if func in self.hooks:
            self.hooks.remove(func)

    async def dispatch_event(self, event):
        for hook in self.hooks:
            await hook(event)

        if isinstance(event, (TrackEndEvent, TrackExceptionEvent, TrackStuckEvent)) and event.player is not None:
            await event.player.handle_event(event)

    async def update_state(self, data):
        g = int(data['guildId'])

        if g in self.players:
            p = self.players.get(g)
            p.position = data['state']['position']
            p.position_timestamp = data['state']['time']

    async def get_tracks(self, query):
        log.debug('Requesting tracks for query ', query)
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

            self.voice_state.update({'sessionId': data['d']['session_id']})

            guild_id = int(data['d']['guild_id'])

            if self.players[guild_id]:
                self.players[guild_id].channel_id = data['d']['channel_id']

        if {'op', 'guildId', 'sessionId', 'event'} == self.voice_state.keys():
            await self.ws.send(**self.voice_state)
            self.voice_state.clear()

    def destroy(self):
        self.ws.destroy()
        self.bot.remove_listener(self.on_socket_response)
        self.hooks.clear()
