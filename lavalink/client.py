import asyncio
import logging
import random
from urllib.parse import quote

import aiohttp

from .node import Node
from .nodemanager import NodeManager
from .playermanager import PlayerManager

log = logging.getLogger(__name__)


class Client:
    """
    Represents a Lavalink client used to manage nodes and connections.

    .. _event loop: https://docs.python.org/3/library/asyncio-eventloops.html

    Parameters
    ----------
    user_id: :class:`str`
        The user id of the bot.
    shard_count: Optional[:class:`int`]
        The amount of shards your bot has.
    pool_size: Optional[:class:`int`]
        The amount of connections to keep in a pool,
        used for HTTP requests and WS connections.
    loop: Optional[event loop]
        The `event loop`_ to use for asynchronous operations.
    """

    def __init__(self, user_id: int, shard_count: int = 1, pool_size: int = 100, loop=None):
        self._user_id = str(user_id)
        self._shard_count = str(shard_count)
        self._loop = loop or asyncio.get_event_loop()
        self.node_manager = NodeManager(self)
        self.players = PlayerManager(self)

        self._session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=pool_size, loop=loop)
        )  # This session will be used for websocket and http requests

    def add_node(self, host: str, port: int, password: str, region: str, name: str = None):
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
        :param name:
            An identifier for the node that will show in logs.
        """
        self.node_manager.add_node(host, port, password, region, name)

    async def get_tracks(self, query: str, node: Node = None):
        """
        Gets all tracks associated with the given query.
        -----------------
        :param query:
            The query to perform a search for.
        :param node:
            The node to use for track lookup. Leave this blank to use a random node.
        """
        node = node or random.choice(self.node_manager.nodes)
        destination = 'http://{}:{}/loadtracks?identifier={}'.format(node.host, node.port, quote(query))
        headers = {
            'Authorization': node.password
        }

        async with self._session.get(destination, headers=headers) as res:
            if res.status == 200:
                return await res.json()

            return []

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
