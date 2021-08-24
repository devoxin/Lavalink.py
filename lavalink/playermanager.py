from .exceptions import NodeException
from .models import BasePlayer
from .node import Node


class PlayerManager:
    """
    Represents the player manager that contains all the players.

    len(x):
        Returns the total amount of cached players.
    iter(x):
        Returns an iterator of all the players cached.

    Attributes
    ----------
    players: :class:`dict`
        Cache of all the players that Lavalink has created.
    default_player: :class:`BasePlayer`
        The player that the player manager is initialized with.
    """

    def __init__(self, lavalink, player):
        if not issubclass(player, BasePlayer):
            raise ValueError(
                'Player must implement BasePlayer or DefaultPlayer.')

        self._lavalink = lavalink
        self.players = {}
        self.default_player = player

    def __len__(self):
        return len(self.players)

    def __iter__(self):
        """ Returns an iterator that yields a tuple of (guild_id, player). """
        for guild_id, player in self.players.items():
            yield guild_id, player

    async def destroy(self, guild_id: int):
        """
        Removes a player from cache, and also Lavalink if applicable.
        Ensure you have disconnected the given guild_id from the voicechannel
        first, if connected.

        Warning
        -------
        This should only be used if you know what you're doing. Players should never be
        destroyed unless they have been moved to another :class:`Node`.

        Parameters
        ----------
        guild_id: int
            The guild_id associated with the player to remove.
        """
        if guild_id not in self.players:
            return

        player = self.players.pop(guild_id)

        if player.node and player.node.available:
            await player.node._send(op='destroy', guildId=player.guild_id)
            player.cleanup()

        self._lavalink._logger.debug(
            '[NODE-{}] Successfully destroyed player {}'.format(player.node.name, guild_id))

    def values(self):
        """ Returns an iterator that yields only values. """
        for player in self.players.values():
            yield player

    def find_all(self, predicate=None):
        """
        Returns a list of players that match the given predicate.

        Parameters
        ----------
        predicate: Optional[:class:`function`]
            A predicate to return specific players. Defaults to `None`.

        Returns
        -------
        List[:class:`DefaultPlayer`]
        """
        if not predicate:
            return list(self.players.values())

        return [p for p in self.players.values() if bool(predicate(p))]

    def remove(self, guild_id: int):
        """
        Removes a player from the internal cache.

        Parameters
        ----------
        guild_id: :class:`int`
            The player that will be removed.
        """
        if guild_id in self.players:
            player = self.players.pop(guild_id)
            player.cleanup()

    def get(self, guild_id: int):
        """
        Gets a player from cache.

        Parameters
        ----------
        guild_id: :class:`int`
            The guild_id associated with the player to get.

        Returns
        -------
        Optional[:class:`DefaultPlayer`]
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

        Parameters
        ----------
        guild_id: :class:`int`
            The guild_id to associate with the player.
        region: :class:`str`
            The region to use when selecting a Lavalink node. Defaults to `eu`.
        endpoint: :class:`str`
            The address of the Discord voice server. Defaults to `None`.
        node: :class:`Node`
            The node to put the player on. Defaults to `None` and a node with the lowest penalty is chosen.

        Returns
        -------
        :class:`DefaultPlayer`
        """
        if guild_id in self.players:
            return self.players[guild_id]

        if endpoint:  # Prioritise endpoint over region parameter
            region = self._lavalink.node_manager.get_region(endpoint)

        best_node = node or self._lavalink.node_manager.find_ideal_node(region)

        if not best_node:
            raise NodeException('No available nodes!')

        self.players[guild_id] = player = self.default_player(guild_id, best_node)
        self._lavalink._logger.debug(
            '[NODE-{}] Successfully created player for {}'.format(best_node.name, guild_id))
        return player
