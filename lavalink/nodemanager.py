# import asyncio
import logging
from .node import Node
from .events import NodeConnectedEvent, NodeDisconnectedEvent

log = logging.getLogger('lavalink')


class NodeManager:
    def __init__(self, lavalink, regions: dict):
        self._lavalink = lavalink
        self.nodes = []
        self.player_queue = []

        self.regions = regions or {
            'asia': ('hongkong', 'singapore', 'sydney', 'japan', 'southafrica'),
            'eu': ('eu', 'amsterdam', 'frankfurt', 'russia', 'london'),
            'us': ('us', 'brazil')
        }

    def __iter__(self):
        for n in self.nodes:
            yield n

    @property
    def available_nodes(self):
        """
        Returns a list of available nodes.
        """
        return [n for n in self.nodes if n.available]

    def add_node(self, host: str, port: int, password: str, region: str, name: str = None,
                 resume_key: str = None, resume_timeout: int = 60):
        """
        Adds a node
        ----------
        :param host:
            The host to which Lavalink server you're connecting to.
        :param port:
            The port to the Lavalink server you're connecting to.
        :param password:
            The password to the Lavalink server you're are connecting to, to authenticate with it.
            Default password is ``youshallnotpass``.
        :param region:
            The region you want your node to connect to.
        :param name:
            The name of your node.
        :param resume_key:
            The resume key of the session you want to resume to.
        :param resume_timeout:
            The amount of time in seconds, that lavalink.py will reconnect to your node from a timeout.
        """
        node = Node(self, host, port, password, region, name, resume_key, resume_timeout)
        self.nodes.append(node)

    def remove_node(self, node: Node):
        """
        Removes a node.
        ----------
        :param node:
            The node to remove from the list
        """
        self.nodes.remove(node)

    def get_region(self, endpoint: str):
        """
        Returns a Lavalink.py-friendly region from a Discord voice server address
        ----------
        :param endpoint:
            The address of the Discord voice server
        """
        if not endpoint:
            return None

        endpoint = endpoint.replace('vip-', '')

        for key in self.regions:
            nodes = [n for n in self.available_nodes if n.region == key]

            if not nodes:
                continue

            if endpoint.startswith(self.regions[key]):
                return key

        return None

    def find_ideal_node(self, region: str = None):
        """
        Finds the best (least used) node in the given region, if applicable.
        ----------
        :param region:
            The region to find a node in.
        """
        nodes = None
        if region:
            nodes = [n for n in self.available_nodes if n.region == region]

        if not nodes:  # If there are no regional nodes available, or a region wasn't specified.
            nodes = self.available_nodes

        if not nodes:
            return None

        best_node = min(nodes, key=lambda node: node.penalty)
        return best_node

    async def _node_connect(self, node: Node):
        log.info('[NODE-{}] Successfully established connection'.format(node.name))
        await self._lavalink._dispatch_event(NodeConnectedEvent(node))

    async def _node_disconnect(self, node: Node, code: int, reason: str):
        log.warning('[NODE-{}] Disconnected with code {} and reason {}'.format(node.name, code, reason))
        await self._lavalink._dispatch_event(NodeDisconnectedEvent(node, code, reason))

        best_node = self.find_ideal_node(node.region)

        if not best_node:
            for player in node.players:
                self.player_queue.append(player)

            await self._wait_for_best_node(node)
            log.error('Unable to move players, no available nodes! Trying to find one to connect to.')
            return

        for player in node.players:
            await player.change_node(best_node)

    async def _wait_for_best_node(self, original_node):
        while True:
            best_node = self.find_ideal_node()

            if best_node:
                for player in self.player_queue:
                    await player.change_node(best_node)
                self.player_queue.clear()
                log.info('Connecting all players that were connected to NODE-{} to NODE-{}'.format(original_node.name, best_node.name))
                return
            # await asyncio.sleep(10) Not sure if I need this here or not
