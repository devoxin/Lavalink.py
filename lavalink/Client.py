import asyncio
import logging
from urllib.parse import quote

import aiohttp

from .Events import TrackEndEvent, TrackExceptionEvent, TrackStuckEvent, PlayerStatusUpdate
from .NodeManager import NodeManager, NoNodesAvailable
from .PlayerManager import DefaultPlayer, PlayerManager

log = logging.getLogger(__name__)


def set_log_level(log_level):
    root_log = logging.getLogger(__name__.split('.')[0])
    root_log.setLevel(log_level)


class Client:
    def __init__(self, bot, log_level=logging.INFO, loop=asyncio.get_event_loop(), default_node: int = 0,
                 player=DefaultPlayer, rest_round_robin: bool = False):
        """
        Creates a new Lavalink client.
        -----------------
        :param bot:
            The bot to attach the Client to.
        :param log_level:
            The log_level to set the client to. Defaults to ``INFO``
        :param loop:
            The event loop for the client.
        :param host:
            Your Lavalink server's host address.
        :param rest_port:
            The port over which the HTTP requests should be made.
        :param password:
            The password for your Lavalink server. The default password is ``youshallnotpass``.
        :param ws_retry:
            How often the client should attempt to reconnect to the Lavalink server.
        :param ws_port:
            The port on which a WebSocket connection to the Lavalink server should be established.
        :param shard_count:
            The bot's shard count. Defaults to ``1``.
        :param player:
            The class that should be used for the player. Defaults to ``DefaultPlayer``.
            Do not change this unless you know what you are doing!
        """

        bot.lavalink = self
        self.http = aiohttp.ClientSession(loop=loop)
        self.hooks = []

        set_log_level(log_level)

        self.bot = bot
        self.bot.add_listener(self.on_socket_response)

        self.loop = loop
        self.new_loop = asyncio.new_event_loop()
        self._server_version = 2
        self.nodes = NodeManager(self, default_node, rest_round_robin, player)
        self.players = PlayerManager(self, player)

    def register_hook(self, func):
        """
        Registers a hook. Since this probably is a bit difficult, I'll explain it in detail.
        A hook basically is an object of a function you pass. This will append that object to a list and whenever
        an event from the Lavalink server is dispatched, the function will be called internally. For declaring the
        function that should become a hook, pass ``event` as its sole parameter.
        Can be a function but also a coroutine.

        Example for a method declaration inside a class:
        ---------------
            self.bot.lavalink.register_hook(my_hook)

            async def my_hook(self, event):
                channel = self.bot.get_channel(event.player.fetch('channel'))
                if not channel:
                    return

                if isinstance(event, lavalink.Events.TrackStartEvent):
                    await channel.send(embed=discord.Embed(title='Now playing:',
                                                           description=event.track.title,
                                                           color=discord.Color.blurple()))
        ---------------
        :param func:
            The function that should be registered as a hook.
        """

        if func not in self.hooks:
            self.hooks.append(func)

    def unregister_hook(self, func):
        """ Unregisters a hook. For further explanation, please have a look at ``register_hook``. """
        if func in self.hooks:
            self.hooks.remove(func)

    async def dispatch_event(self, event):
        """ Dispatches an event to all registered hooks. """
        log.debug('Dispatching event of type {} to {} hooks'.format(event.__class__.__name__, len(self.hooks)))
        for hook in self.hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(event)
                else:
                    hook(event)
            except Exception as e:  # pylint: disable=broad-except
                # Catch generic exception thrown by user hooks
                log.warning(
                    'Encountered exception while dispatching an event to hook `{}` ({})'.format(hook.__name__, str(e)))

        if isinstance(event, (TrackEndEvent, TrackExceptionEvent, TrackStuckEvent)) and event.player:
            await event.player.handle_event(event)

    async def update_state(self, data):
        """ Updates a player's state when a payload with opcode ``playerUpdate`` is received. """
        guild_id = int(data['guildId'])

        if guild_id in self.players:
            player = self.players[guild_id]
            if not player:
                return
            player.position = data['state'].get('position', 0)
            player.position_timestamp = data['state']['time']
            await self.dispatch_event(PlayerStatusUpdate(player, player.current))

    async def get_tracks(self, query):
        """ Returns a Dictionary containing search results for a given query. """
        log.debug('Requesting tracks for query {}'.format(query))
        node = self.nodes.get_rest()
        async with self.http.get(node.rest_uri + quote(query), headers={'Authorization': node.password}) as res:
            return await res.json(content_type=None)

    async def get_player(self, guild_id: int, create: bool = True):
        """ Gets or creates a player and determines which node is the best for it. """
        try:
            await asyncio.wait_for(self.nodes.ready.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            raise NoNodesAvailable
        if guild_id in self.players:
            return self.players[guild_id]
        if not create:
            return None
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return self.players.get(guild_id, self.nodes.nodes[0])
        return self.nodes.get_by_region(guild)

    # Bot Events
    async def on_socket_response(self, data):
        """
        This coroutine will be called every time an event from Discord is received.
        It is used to update a player's voice state through forwarding a payload via the WebSocket connection to Lavalink.
        -------------
        :param data:
            The payload received from Discord.
        """

        await self.nodes.ready.wait()

        # INTERCEPT VOICE UPDATES
        if not data or data.get('t', '') not in ['VOICE_STATE_UPDATE', 'VOICE_SERVER_UPDATE']:
            return

        guild_id = int(data['d']['guild_id'])
        player = self.players[guild_id]
        if not player:
            log.debug('Client received an update for a non-existent player. {}'.format(guild_id))
            return

        if data['t'] == 'VOICE_SERVER_UPDATE':
            player._voice_state.update({
                'op': 'voiceUpdate',
                'guildId': data['d']['guild_id'],
                'event': data['d']
            })
            log.debug('Voice server update: {}'.format(str(data)))
        else:
            if int(data['d']['user_id']) != self.bot.user.id:
                return

            player._voice_state.update({'sessionId': data['d']['session_id']})

            player.channel_id = data['d']['channel_id']

            log.debug('Voice state update: {}'.format(str(data)))

        if {'op', 'guildId', 'sessionId', 'event'} == player._voice_state.keys():
            log.debug('Sending voice update to lavalink: {}'.format(str(player._voice_state)))
            await player.node.ws.send(**player._voice_state)
            player._voice_lock.set()

    def destroy(self):
        """ Destroys the Lavalink client. """
        for node in self.nodes:
            node.ws.destroy()
        self.bot.remove_listener(self.on_socket_response)
        self.hooks.clear()
