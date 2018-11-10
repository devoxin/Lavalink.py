from .node import Node


class NodeManager:
    def __init__(self, lavalink):
        self._lavalink = lavalink
        self.nodes = []
