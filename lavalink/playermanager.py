from .node import Node
from .models import DefaultPlayer


class PlayerManager:
    def __init__(self, lavalink):
        self._lavalink = lavalink
        self.players = {}

    def __iter__(self):
        """ Returns an iterator that yields a tuple of (guild_id, player). """
        for guild_id, player in self.players.items():
            yield guild_id, player

    def values(self):
        """ Returns an iterator that yields only values """
        for player in self.players.values():
            yield player

    def get(self, guild_id: int):
        """
        Gets a player from cache
        ----------
        :param guild_id:
            The guild_id associated with the player to get
        """
        return self.players.get(guild_id)

    def create(self, guild_id: int, region: str = 'eu', endpoint: str = None, node: Node = None):
        """
        Creates a player if one doesn't exist with the given information.

        If node is provided, a player will be created on that node.
        If region is provided, a player will be created on a node in the given region.
        If endpoint is provided, Lavalink.py will attempt to parse the region from the endpoint
        and return a node in the parsed region.

        If node, region and endpoint are left unspecified, or region/endpoint selection fails,
        Lavalink.py will fall back to the node with the lowest penalty.

        Region can be omitted if node is specified and vice-versa.
        ----------
        :param guild_id:
            The guild_id to associate with the player
        :param region:
            The region to use when selecting a Lavalink node
        :param node:
            The node to put the player on
        """
        if guild_id in self.players:
            return self.players[guild_id]

        if node:
            return node

        if endpoint:
            region = self._lavalink.node_manager.get_region(endpoint)

        node = self._lavalink.node_manager.find_ideal_node(region)

        if not node:
            raise Exception('No available nodes!')  # TODO: NodeException or something

        self.players[guild_id] = player = DefaultPlayer(guild_id, node)
        return player