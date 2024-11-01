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
from typing import (TYPE_CHECKING, Callable, Dict, Final, Generic, Iterator, Optional,
                    Tuple, Type, TypeVar, Union, overload)

from .errors import ClientError, RequestError
from .node import Node
from .player import BasePlayer

if TYPE_CHECKING:
    from .client import Client

_log = logging.getLogger(__name__)

PlayerT = TypeVar('PlayerT', bound=BasePlayer)
CustomPlayerT = TypeVar('CustomPlayerT', bound=BasePlayer)


class PlayerManager(Generic[PlayerT]):
    """
    Represents the player manager that contains all the players.

    len(x):
        Returns the total number of stored players.
    iter(x):
        Returns an iterator of all the stored players.

    Attributes
    ----------
    client: :class:`Client`
        The Lavalink client.
    players: Dict[int, :class:`BasePlayer`]
        Cache of all the players that Lavalink has created.
    """
    __slots__ = ('client', '_player_cls', 'players')

    def __init__(self, client, player: Type[PlayerT]):
        if not issubclass(player, BasePlayer):
            raise ValueError('Player must implement BasePlayer.')

        self.client: Final['Client'] = client
        self._player_cls: Final[Type[PlayerT]] = player
        self.players: Final[Dict[int, PlayerT]] = {}

    def __len__(self) -> int:
        return len(self.players)

    def __iter__(self) -> Iterator[Tuple[int, PlayerT]]:
        """ Returns an iterator that yields a tuple of (guild_id, player). """
        yield from self.players.items()

    def values(self) -> Iterator[PlayerT]:
        """ Returns an iterator that yields only values. """
        yield from self.players.values()

    def find_all(self, predicate: Optional[Callable[[PlayerT], bool]] = None):
        """
        Returns a list of players that match the given predicate.

        Parameters
        ----------
        predicate: Optional[Callable[[:class:BasePlayer], bool]]
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

    def get(self, guild_id: int) -> Optional[PlayerT]:
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

    @overload
    def create(self,
               guild_id: int,
               *,
               region: Optional[str] = ...,
               endpoint: Optional[str] = ...,
               node: Optional[Node] = ...) -> PlayerT:
        ...

    @overload
    def create(self,
               guild_id: int,
               *,
               region: Optional[str] = ...,
               endpoint: Optional[str] = ...,
               node_filter: Optional[Callable[[Node], bool]] = ...) -> PlayerT:
        ...

    @overload
    def create(self,
               guild_id: int,
               *,
               region: Optional[str] = ...,
               endpoint: Optional[str] = ...,
               node: Optional[Node] = ...,
               cls: Type[CustomPlayerT]) -> CustomPlayerT:
        ...

    @overload
    def create(self,
               guild_id: int,
               *,
               region: Optional[str] = ...,
               endpoint: Optional[str] = ...,
               node_filter: Optional[Callable[[Node], bool]] = ...,
               cls: Type[CustomPlayerT]) -> CustomPlayerT:
        ...

    def create(self,
               guild_id: int,
               *,
               region: Optional[str] = None,
               endpoint: Optional[str] = None,
               node: Optional[Node] = None,
               node_filter: Optional[Callable[[Node], bool]] = None,
               cls: Optional[Type[CustomPlayerT]] = None) -> Union[CustomPlayerT, PlayerT]:
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
            The region to use when selecting a Lavalink node.
            Defaults to ``None``.
        endpoint: Optional[:class:`str`]
            The address of the Discord voice server.
            Defaults to ``None``.
        node: Optional[:class:`Node`]
            The node to put the player on.
            Defaults to ``None``, which selects the node with the lowest penalty.
        node_filter: Optional[Callable[[:class:`Node`], :class:`bool`]]
            A filter to use when selecting nodes this player can be assigned to.
            This cannot be used with the ``node`` parameter.
            Nodes are filtered based on the given predicate, and then again based on their penalty score.
            If no nodes are found after filtering, all available nodes will be considered without filtering.
        cls: Optional[Type[:class:`BasePlayer`]]
            The player class to use when instantiating a new player.
            Defaults to ``None`` which uses the player class provided to :class:`Client`.
            If no class was provided, this will typically be :class:`DefaultPlayer`.

            Warning
            -------
            This function could return a player of a different type to that specified in ``cls``,
            if a player was created before with a different class type.

        Raises
        ------
        :class:`ValueError`
            If the provided ``cls`` is not a valid subclass of :class:`BasePlayer`.

        Returns
        -------
        :class:`BasePlayer`
            A class that inherits ``BasePlayer``. By default, the actual class returned will
            be :class:`DefaultPlayer`, however if you have specified a custom player implementation,
            then this will be different.
        """
        if guild_id in self.players:
            return self.players[guild_id]

        cls = cls or self._player_cls  # type: ignore

        if not issubclass(cls, BasePlayer):  # type: ignore
            raise ValueError('Player must implement BasePlayer.')

        if node is not None and node_filter is not None:
            raise ValueError('node and node_filter may not be specified together')

        if node_filter is not None:
            user_filtered = [n for n in self.client.node_manager.available_nodes if node_filter(n)]

            if user_filtered:
                node = min(user_filtered, key=lambda node: node.penalty)

        if node is None and endpoint is not None:  # Prioritise endpoint over region parameter
            region = self.client.node_manager.get_region(endpoint)

        best_node = node or self.client.node_manager.find_ideal_node(region)

        if not best_node:
            raise ClientError('No available nodes!')

        id_int = int(guild_id)
        player = cls(id_int, best_node)
        self.players[id_int] = player  # type: ignore
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
        if guild_id in self.players:
            player = self.players.pop(guild_id)
            player.cleanup()

            if player.node:
                await player.node.destroy_player(player._internal_id)

            _log.debug('Destroyed player with GuildId %d on node \'%s\'', guild_id, player.node.name if player.node else 'UNASSIGNED')
        else:
            for node in self.client.node_manager:
                try:
                    await node.destroy_player(guild_id)
                except RequestError:  # Should never happen anyway
                    pass
