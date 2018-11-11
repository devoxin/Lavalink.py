from .node import Node
from .models import DefaultPlayer


class PlayerManager:
    def __init__(self, lavalink):
        self._lavalink = lavalink
        self.players = {}

    def get(self, guild_id: int):
        """
        Gets a player from cache
        ----------
        :param guild_id:
            The guild_id associated with the player to get
        """
        if guild_id in self.players:
            return self.players[guild_id]

        return None

    def create(self, guild_id: int, region: str = 'us', node: Node = None):
        """
        Creates a player if one doesn't exist with the given information.
        If node is provided, a player will be created on that node, otherwise
        a player will be created on the best node in the given region (defaults to US).

        Region can be omitted if node is specified and vice-versa.
        ----------
        :param guild_id:
            The guild_id to associate with the player
        :param region:
            The region to use when selecting a Lavalink node
        :param node:
            The node to put the player on
        """
        if node:
            return node

        node = self._lavalink.node_manager.find_ideal_node(region)

        if not node:
            raise Exception('send nodes')

        self.players[guild_id] = player = DefaultPlayer(guild_id, node)
        return player
