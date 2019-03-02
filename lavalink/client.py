import asyncio
import logging
import random
import inspect
from urllib.parse import quote

import aiohttp

from .models import DefaultPlayer
from .node import Node
from .nodemanager import NodeManager
from .playermanager import PlayerManager
from .events import Event

log = logging.getLogger('lavalink')


class Client:
    """
    Represents a Lavalink client used to manage nodes and connections.

    .. _event loop: https://docs.python.org/3/library/asyncio-eventloops.html

    Parameters
    ----------
    user_id: int
        The user id of the bot.
    shard_count: Optional[int]
        The amount of shards your bot has.
    pool_size: Optional[int]
        The amount of connections to keep in a pool,
        used for HTTP requests and WS connections.
    loop: Optional[event loop]
        The `event loop`_ to use for asynchronous operations.
    player: Optional[BasePlayer]
        The class that should be used for the player. Defaults to ``DefaultPlayer``.
        Do not change this unless you know what you are doing!
    regions: Optional[dict]
        A dictionary representing region -> discord endpoint. You should only
        change this if you know what you're doing and want more control over
        which regions handle specific locations.
    """

    def __init__(self, user_id: int, shard_count: int = 1, pool_size: int = 100, loop=None, player=DefaultPlayer,
                 regions: dict = None):
        self._user_id = str(user_id)
        self._shard_count = str(shard_count)
        self._loop = loop or asyncio.get_event_loop()
        self.node_manager = NodeManager(self, regions)
        self.players = PlayerManager(self, player)

        self._event_hooks = []

        self._session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=pool_size, loop=loop),
            timeout=aiohttp.ClientTimeout(total=30)
        )  # This session will be used for websocket and http requests.

    def add_event_hook(self, hook):
        if hook not in self._event_hooks:
            self._event_hooks.append(hook)

    def add_node(self, host: str, port: int, password: str, region: str,
                 resume_key: str = None, resume_timeout: int = 60, name: str = None):
        """
        Adds a node to Lavalink's node manager.
        ----------
        :param host:
            The address of the Lavalink node.
        :param port:
            The port to use for websocket and REST connections.
        :param password:
            The password used for authentication.
        :param region:
            The region to assign this node to.
        :param resume_key:
            A resume key used for resuming a session upon re-establishing a WebSocket connection to Lavalink.
        :param resume_timeout:
            How long the node should wait for a connection while disconnected before clearing all players.
        :param name:
            An identifier for the node that will show in logs.
        """
        self.node_manager.add_node(host, port, password, region, name, resume_key, resume_timeout)

    async def get_tracks(self, query: str, node: Node = None):
        """|coro|

        Gets all tracks associated with the given query.
        -----------------
        :param query:
            The query to perform a search for.
        :param node:
            The node to use for track lookup. Leave this blank to use a random node.
        """
        node = node or random.choice(self.node_manager.available_nodes)
        destination = 'http://{}:{}/loadtracks?identifier={}'.format(node.host, node.port, quote(query))
        headers = {
            'Authorization': node.password
        }

        async with self._session.get(destination, headers=headers) as res:
            if res.status == 200:
                return await res.json()

            return []

    async def decode_track(self, track: str, node: Node = None):
        """|coro|

        Decodes a base64-encoded track string into a dict.

        Parameters
        ----------
        track: str
            The base64-encoded `track` string.
        node: Node
            The node to use for the query. ``None`` means random.

        Returns
        ---------
        A dict representing the track's information.
        """
        node = node or random.choice(self.node_manager.available_nodes)
        destination = 'http://{}:{}/decodetrack?track={}'.format(node.host, node.port, track)
        headers = {
            'Authorization': node.password
        }

        async with self._session.get(destination, headers=headers) as res:
            if res.status == 200:
                return await res.json()

            return None

    async def decode_tracks(self, tracks: list, node: Node = None):
        """|coro|

        Decodes a list of base64-encoded track strings into a dict.

        Parameters
        ----------
        track: list[str]
            A list of base64-encoded `track` strings.
        node: Node
            The node to use for the query. ``None`` means random.

        Returns
        ---------
        An array of dicts representing track information.
        """
        node = node or random.choice(self.node_manager.available_nodes)
        destination = 'http://{}:{}/decodetracks'.format(node.host, node.port)
        headers = {
            'Authorization': node.password
        }

        async with self._session.post(destination, headers=headers, json=tracks) as res:
            if res.status == 200:
                return await res.json()

            return None

    async def voice_update_handler(self, data):
        """|coro|

        This function intercepts websocket data from your Discord library and
        forwards the relevant information on to Lavalink, which is used to
        establish a websocket connection and send audio packets to Discord.

        -------------
        :example:
            bot.add_listener(lavalink_client.voice_update_handler, 'on_socket_response')

        :param data:
            The payload received from Discord.
        """
        if not data or 't' not in data:
            return

        if data['t'] == 'VOICE_SERVER_UPDATE':
            guild_id = int(data['d']['guild_id'])
            player = self.players.get(guild_id)

            if player:
                await player._voice_server_update(data['d'])
        elif data['t'] == 'VOICE_STATE_UPDATE':
            if int(data['d']['user_id']) != int(self._user_id):
                return

            guild_id = int(data['d']['guild_id'])
            player = self.players.get(guild_id)

            if player:
                await player._voice_state_update(data['d'])
        else:
            return

    async def _dispatch_event(self, event: Event):
        """|coro|

        Dispatches the given event to all registered hooks
        ----------
        :param event:
            The event to dispatch to the hooks
        """
        for hook in self._event_hooks:
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(event)
                else:
                    hook(event)
            except Exception as e:  # pylint: disable=W0703
                log.warning('Event hook {} encountered an exception!'.format(hook.__name__), e)
