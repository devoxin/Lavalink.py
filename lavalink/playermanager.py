"""
MIT License

Copyright (c) 2017-present Devoxin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import logging

from .errors import NodeError
from .models import BasePlayer
from .node import Node

_log = logging.getLogger(__name__)


class PlayerManager:
    """
    Represents the player manager that contains all the players.

    len(x):
        Returns the total number of stored players.
    iter(x):
        Returns an iterator of all the stored players.

    Attributes
    ----------
    players: :class:`dict`
        Cache of all the players that Lavalink has created.
    """

    def __init__(self, lavalink, player):
        if not issubclass(player, BasePlayer):
            raise ValueError(
                'Player must implement BasePlayer or DefaultPlayer.')

        self._lavalink = lavalink
        self._player_cls = player
        self.players = {}

    def __len__(self):
        return len(self.players)

    def __iter__(self):
        """ Returns an iterator that yields a tuple of (guild_id, player). """
        for guild_id, player in self.players.items():
            yield guild_id, player

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
            A predicate to return specific players. Defaults to ``None``.

        Returns
        -------
        List[:class:`BasePlayer`]
            This could be a :class:`DefaultPlayer` if no custom player implementation
            was provided.
        """
        if not predicate:
            return list(self.players.values())

        return [p for p in self.players.values() if bool(predicate(p))]

    def get(self, guild_id: int):
        """
        Gets a player from cache.

        Parameters
        ----------
        guild_id: :class:`int`
            The guild_id associated with the player to get.

        Returns
        -------
        Optional[:class:`BasePlayer`]
            This could be a :class:`DefaultPlayer` if no custom player implementation
            was provided.
        """
        return self.players.get(guild_id)

    def remove(self, guild_id: int):
        """
        Removes a player from the internal cache.

        Parameters
        ----------
        guild_id: :class:`int`
            The player to remove from cache.
        """
        if guild_id in self.players:
            player = self.players.pop(guild_id)
            player.cleanup()

    def create(self, guild_id: int, region: str = None, endpoint: str = None, node: Node = None):
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
        region: Optional[:class:`str`]
            The region to use when selecting a Lavalink node. Defaults to ``None``.
        endpoint: Optional[:class:`str`]
            The address of the Discord voice server. Defaults to ``None``.
        node: Optional[:class:`Node`]
            The node to put the player on. Defaults to ``None`` and a node with the lowest penalty is chosen.

        Returns
        -------
        :class:`BasePlayer`
            A class that inherits ``BasePlayer``. By default, the actual class returned will
            be :class:`DefaultPlayer`, however if you have specified a custom player implementation,
            then this will be different.
        """
        if guild_id in self.players:
            return self.players[guild_id]

        if endpoint:  # Prioritise endpoint over region parameter
            region = self._lavalink.node_manager.get_region(endpoint)

        best_node = node or self._lavalink.node_manager.find_ideal_node(region)

        if not best_node:
            raise NodeError('No available nodes!')

        id_int = int(guild_id)
        self.players[id_int] = player = self._player_cls(id_int, best_node)
        _log.debug('Created player with GuildId %d on node \'%s\'', id_int, best_node.name)
        return player

    async def destroy(self, guild_id: int):
        """|coro|

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
        player.cleanup()

        if player.node:
            await player.node._send(op='destroy', guildId=player._internal_id)

        _log.debug('Destroyed player with GuildId %d on node \'%s\'', guild_id, player.node.name if player.node else 'UNASSIGNED')
