from .node import Node


class NodeManager:
    def __init__(self, lavalink, default_region: str = 'eu'):  # This is only temporary, while I experiment
        self._lavalink = lavalink
        self.nodes = []

        self.default_region = default_region
        self.default_regions = {
            'asia': ['hongkong', 'singapore', 'sydney'],
            'eu': ['eu', 'amsterdam', 'frankfurt', 'russia'],
            'us': ['us', 'brazil'],
        }

    def get_region(self, endpoint: str):
        if not endpoint:
            return self.default_region

        for key in self.default_regions.keys():
            nodes = [n for n in self.nodes if n.region == key]

            if len(nodes) == 0 or not any(n.available for n in nodes):
                continue

            for region in self.default_regions[key]:
                if endpoint.startswith(region):
                    return key

        return self.default_region

    def find_ideal_node(self, region: str = None):
        nodes = None
        if region:
            nodes = [n for n in self.nodes if n.region == region and n.available]

        if not nodes:  # If there are no regional nodes available, or a region wasn't specified.
            nodes = [n for n in self.nodes if n.available]

        # TODO: Sort nodes based on penalties
        return nodes[0] if len(nodes) > 0 else None

    def add_node(self, host: str, port: int, password: str, region: str):
        node = Node(self, host, port, password, region)
        self.nodes.append(node)
