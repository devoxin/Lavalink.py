from .node import Node
from .events import NodeConnectedEvent, NodeDisconnectedEvent


class NodeManager:
    def __init__(self, lavalink, regions: dict):
        self._lavalink = lavalink
        self._player_queue = []
        self._original_player_nodes = {}

        self.nodes = []

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
        Adds a node to your Lavalink server.
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
        node = Node(self, host, port, password, region, name, resume_key, resume_timeout)
        self.nodes.append(node)

        self._lavalink._logger.info('[NODE-{}] Successfully added to Node Manager'.format(node.name))

    def remove_node(self, node: Node):
        """
        Removes a node.
        ----------
        :param node:
            The node to remove from the list.
        """
        self.nodes.remove(node)
        self._lavalink._logger.info('[NODE-{}] Successfully removed Node'.format(node.name))

    def get_region(self, endpoint: str):
        """
        Returns a Lavalink.py-friendly region from a Discord voice server address.
        ----------
        :param endpoint:
            The address of the Discord voice server.
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
        self._lavalink._logger.info('[NODE-{}] Successfully established connection'.format(node.name))

        for player in self._player_queue:
            await player.change_node(node)
            self._lavalink._logger.debug('[NODE-{}] Successfully moved {}'.format(node.name, player.guild_id))

        for player in node._original_players:
            player.change_node(node)

        self._player_queue.clear()
        await self._lavalink._dispatch_event(NodeConnectedEvent(node))

    async def _node_disconnect(self, node: Node, code: int, reason: str):
        self._lavalink._logger.warning('[NODE-{}] Disconnected with code {} and reason {}'.format(node.name, code,
                                                                                                  reason))
        await self._lavalink._dispatch_event(NodeDisconnectedEvent(node, code, reason))

        best_node = self.find_ideal_node(node.region)

        if not best_node:
            self._player_queue.extend(node.players)
            self._lavalink._logger.error('Unable to move players, no available nodes! '
                                         'Waiting for a node to become available.')
            return

        for player in node.players:
            await player.change_node(best_node)
