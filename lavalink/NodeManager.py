from .WebSocket import WebSocket
from .Stats import Stats
import asyncio


DISCORD_REGIONS = []


class LavalinkNode:
    def __init__(self, client, host, rest_port, password, ws_port, ws_retry, shard_count, regions):
        self.regions = regions
        self._lavalink = client
        self.rest_uri = 'http://{}:{}/loadtracks?identifier='.format(host, rest_port)
        self.password = password

        self.ws = WebSocket(
            client, self, host, password, ws_port, ws_retry, shard_count
        )
        self.stats = Stats()


class NodeManager:
    def __init__(self, lavalink, default_node, round_robin):
        self._lavalink = lavalink
        self.default_node_index = default_node
        self.round_robin = round_robin
        self.ready = asyncio.Event(loop=self._lavalink.loop)
        self.nodes = []
        self.nodes_by_region = {}
