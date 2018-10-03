import asyncio
import logging

from .PlayerManager import PlayerManager, DefaultPlayer
from .Stats import Stats
from .WebSocket import WebSocket

log = logging.getLogger(__name__)
DISCORD_REGIONS = ["amsterdam", "brazil", "eu_central", "eu_west", "frankfurt", "hongkong", "japan", "london", "russia",
                   "singapore", "southafrica", "sydney", "us_central", "us_east", "us_south", "us_west",
                   "vip_amsterdam", "vip_us_east", "vip_us_west"]


class RegionNotFound(Exception):
    pass


class UnreachableNodes(Exception):
    pass


class Regions:
    def __init__(self, region_list: list = None):
        self.regions = region_list or DISCORD_REGIONS
        for r in self.regions:
            if r not in DISCORD_REGIONS:
                raise RegionNotFound

    def __iter__(self):
        for r in self.regions:
            yield r

    @classmethod
    def all(cls):
        return cls()

    @classmethod
    def eu(cls):
        """ All servers in Europe including Russia, because majority of population is closer to EU. """
        return cls(["amsterdam", "eu_central", "eu_west", "frankfurt", "london", "russia", "vip_amsterdam"])

    @classmethod
    def us(cls):
        """ All servers located in United States """
        return cls(["us_central", "us_east", "us_south", "us_west", "vip_us_east", "vip_us_west"])

    @classmethod
    def america(cls):
        """ All servers in North and South America. """
        return cls(["us_central", "us_east", "us_south", "us_west", "vip_us_east", "vip_us_west", "brazil"])

    @classmethod
    def africa(cls):
        """ All servers in Africa. """
        return cls(["southafrica"])

    @classmethod
    def asia(cls):
        """ All servers located in Asia """
        return cls(["hongkong", "japan", "singapore"])

    @classmethod
    def oceania(cls):
        """ All servers located in Australia """
        return cls(["sydney"])

    @classmethod
    def half_one(cls):
        """ EU, Africa, Brazil and East US """
        return cls(["amsterdam", "brazil", "eu_central", "eu_west", "frankfurt", "london", "southafrica",
                    "us_east", "vip_amsterdam", "vip_us_east"])

    @classmethod
    def half_two(cls):
        """ West US, Asia and Oceania """
        return cls(["hongkong", "japan", "russia", "singapore", "sydney", "us_central", "us_south", "us_west",
                    "vip_us_west"])

    @classmethod
    def third_one(cls):
        """ EU, Russia and Africa """
        return cls(["amsterdam", "eu_central", "eu_west", "frankfurt", "london", "russia", "southafrica",
                    "vip_amsterdam"])

    @classmethod
    def third_two(cls):
        """ Asia and Oceania """
        return cls(["hongkong", "japan", "singapore", "sydney"])

    @classmethod
    def third_three(cls):
        """ North and South America """
        return cls(["us_central", "us_east", "us_south", "us_west", "vip_us_east", "vip_us_west"])


class LavalinkNode:
    def __init__(self, manager, host, password, regions, rest_port: int = 2333, ws_port: int = 80,
                 ws_retry: int = 10, shard_count: int = 1):
        self.regions = regions
        self._lavalink = manager._lavalink
        self.manager = manager
        self.rest_uri = 'http://{}:{}/loadtracks?identifier='.format(host, rest_port)
        self.password = password

        self.ws = WebSocket(
            manager._lavalink, self, host, password, ws_port, ws_retry, shard_count
        )
        self.server_version = 2
        self.stats = Stats()

        self.ready = asyncio.Event(loop=self._lavalink.loop)

        self.players = PlayerManager(self._lavalink, self, DefaultPlayer)

    def set_online(self):
        self.manager.on_node_ready(self)

    def set_offline(self):
        self.manager.on_node_disabled(self)


class NodeManager:
    def __init__(self, lavalink, default_node, round_robin):
        self._lavalink = lavalink  # lavalink client

        self.default_node_index = default_node  # index of the default node for REST
        self.round_robin = round_robin  # enable round robin load balancing
        self._rr_pos = 0  # starting sound robin position

        self.nodes = []  # list of nodes (online)
        self.offline_nodes = []  # list of nodes (offline or not set-up yet)
        self.nodes_by_region = {}  # dictionary of nodes with region keys

        self.ready = asyncio.Event(loop=self._lavalink.loop)

    def __iter__(self):
        for node in self.nodes:
            yield node

    def on_node_ready(self, node):
        if node not in self.offline_nodes:
            return
        node_index = self.offline_nodes.index(node)
        log.info("Node {} is ready for use.".format(node_index))
        self.nodes.append(self.offline_nodes.pop(node_index))
        node.ready.set()
        self.ready.set()
        for region in node.regions:
            self.nodes_by_region.update({region: node})

    def on_node_disabled(self, node):
        if node not in self.nodes:
            return
        node_index = self.nodes.index(node)
        self.offline_nodes.append(self.nodes.pop(node_index))
        node.ready.clear()
        if not self.nodes:
            self.ready.clear()
        log.info("Node {} was removed from use.".format(node_index))
        if not self.nodes:
            log.warning("Node {} is offline and it's the only node in the cluster.".format(node_index))
            return
        default_node = self.nodes[0]
        for region in node.regions:
            self.nodes_by_region.update({region: default_node})

    def add(self, regions: Regions, host='localhost', rest_port=2333, password='', ws_retry=10, ws_port=80,
            shard_count=1):
        node = LavalinkNode(self, host, password, regions, rest_port, ws_port, ws_retry, shard_count)
        self.offline_nodes.append(node)

    def get_rest(self):
        if not self.nodes:
            raise UnreachableNodes
        node = self.nodes[self.default_node_index] if self.default_node_index < len(self.nodes) else None
        if node is None and self.round_robin is False:
            node = self.nodes[0]
        if self.round_robin is True:
            node = self.nodes[min(self._rr_pos, len(self.nodes) - 1)]
            self._rr_pos += 1
            if self._rr_pos > len(self.nodes):
                self._rr_pos = 0
        return node

    def get_by_region(self, region):
        node = self.nodes_by_region.get(region, None)
        if node is None:
            node = self.nodes[0]
        return node
