import asyncio
import logging
import random
import itertools
from urllib.parse import quote

import aiohttp

from .models import DefaultPlayer
from .node import Node
from .nodemanager import NodeManager
from .playermanager import PlayerManager
from .events import Event

_event_hooks = {}


class Client:
    """
    Represents a Lavalink client used to manage nodes and connections.

    .. _event loop: https://docs.python.org/3/library/asyncio-eventloop.html

    Parameters
    ----------
    user_id: int
        The user id of the bot.
    shard_count: Optional[int]
        The amount of shards your bot has.
    loop: Optional[event loop]
        The `event loop`_ to use for asynchronous operations.
    player: Optional[BasePlayer]
        The class that should be used for the player. Defaults to ``DefaultPlayer``.
        Do not change this unless you know what you are doing!
    regions: Optional[dict]
        A dictionary representing region -> discord endpoint. You should only
        change this if you know what you're doing and want more control over
        which regions handle specific locations.
    connect_back: Optional[bool]
        A boolean that determines if a player will connect back to the
        node it was originally connected to. This is not recommended to do since
        the player will most likely be performing better in the new node.
    """

    def __init__(self, user_id: int, shard_count: int = 1,
                 loop=None, player=DefaultPlayer, regions: dict = None, connect_back: bool = False):
        self._user_id = str(user_id)
        self._connect_back = connect_back
        self._shard_count = str(shard_count)
        self._loop = loop or asyncio.get_event_loop()
        self.node_manager = NodeManager(self, regions)
        self.player_manager = PlayerManager(self, player)
        self._logger = logging.getLogger('lavalink')

        self._session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(loop=loop),
            timeout=aiohttp.ClientTimeout(total=30)
        )  # This session will be used for websocket and http requests.

    def add_node(self, host: str, port: int, password: str, region: str,
                 resume_key: str = None, resume_timeout: int = 60, name: str = None):
        """
        Adds a node to Lavalink's node manager.

        Parameters
        ----------
        host: str
            The address of the Lavalink node.
        port: int
            The port to use for websocket and REST connections.
        password: str
            The password used for authentication.
        region: str
            The region to assign this node to.
        resume_key: Optional[str]
            A resume key used for resuming a session upon re-establishing a WebSocket connection to Lavalink.
        resume_timeout: Optional[int]
            How long the node should wait for a connection while disconnected before clearing all players.
        name: Optional[str]
            An identifier for the node that will show in logs.
        """
        self.node_manager.add_node(host, port, password, region, resume_key, resume_timeout, name)

    async def get_tracks(self, query: str, node: Node = None):
        """|coro|

        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: str
            The query to perform a search for.
        node: Optional[Node]
            The node to use for track lookup. Leave this blank to use a random node.

        Returns
        ----------
        A dict representing tracks.
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
        node: Optional[Node]
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
        tracks: list[str]
            A list of base64-encoded `track` strings.
        node: Optional[Node]
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

        Example
        ----------
        ```bot.add_listener(lavalink_client.voice_update_handler,
                            'on_socket_response')```

        Parameters
        ----------
        data: dict
            The payload received from Discord.
        """
        if not data or 't' not in data:
            return

        if data['t'] == 'VOICE_SERVER_UPDATE':
            guild_id = int(data['d']['guild_id'])
            player = self.player_manager.get(guild_id)

            if player:
                await player._voice_server_update(data['d'])
        elif data['t'] == 'VOICE_STATE_UPDATE':
            if int(data['d']['user_id']) != int(self._user_id):
                return

            guild_id = int(data['d']['guild_id'])
            player = self.player_manager.get(guild_id)

            if player:
                await player._voice_state_update(data['d'])
        else:
            return

    async def _dispatch_event(self, event: Event):
        """|coro|

        Dispatches the given event to all registered hooks.

        Parameters
        ----------
        event: Event
            The event to dispatch to the hooks.
        """
        generic_hooks = _event_hooks.get('Generic', [])
        targeted_hooks = _event_hooks.get(event, [])

        tasks = [hook(event) for hook in itertools.chain(generic_hooks, targeted_hooks)]

        results = await asyncio.gather(*tasks)

        for index, result in enumerate(results):
            if isinstance(result, Exception):
                self._logger.warning('Event hook {} encountered an exception!'.format(tasks[index].__name__), result)
                raise result

        self._logger.info('Dispatched {} event to all registered hooks'.format(event.__name__))
