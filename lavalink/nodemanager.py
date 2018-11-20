from .node import Node


class NodeManager:
    def __init__(self, lavalink, default_region: str = 'eu'):  # This is only temporary, while I experiment
        self._lavalink = lavalink
        self.nodes = []

        self.default_region = default_region
        self.default_regions = {
            'asia': ('hongkong', 'singapore', 'sydney', 'japan', 'southafrica'),
            'eu': ('eu', 'amsterdam', 'frankfurt', 'russia', 'vip-amsterdam', 'london'),
            'us': ('us', 'brazil', 'vip-us')
        }

    def add_node(self, host: str, port: int, password: str, region: str, name: str = None):
        """
        Adds a node
        ----------
        TODO
        """
        node = Node(self, host, port, password, region, name)
        self.nodes.append(node)

    def remove_node(self, node: Node):
        """
        Removes a node
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
            return self.default_region

        for key in self.default_regions:
            nodes = [n for n in self.nodes if n.region == key]

            if not nodes or not any(n.available for n in nodes):
                continue

            if endpoint.startswith(self.default_regions[key]):
                return key

        return self.default_region

    def find_ideal_node(self, region: str = None):
        """
        Finds the best (least used) node in the given region, if applicable.
        ----------
        :param region:
            The region to find a node in.
        """
        nodes = None
        if region:
            nodes = [n for n in self.nodes if n.region == region and n.available]

        if not nodes:  # If there are no regional nodes available, or a region wasn't specified.
            nodes = [n for n in self.nodes if n.available]

        if not nodes:
            return None

        best_node = min(nodes, key=lambda node: node.penalty)
        return best_node
