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
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple

from .errors import ClientError
from .node import Node

if TYPE_CHECKING:
    from .client import Client
    from .abc import BasePlayer

_log = logging.getLogger(__name__)
DEFAULT_REGIONS = {
    'asia': ('hongkong', 'singapore', 'sydney', 'japan', 'southafrica', 'india'),
    'eu': ('rotterdam', 'russia'),
    'us': ('us-central', 'us-east', 'us-south', 'us-west', 'brazil')
}


class NodeManager:
    """Represents the node manager that contains all lavalink nodes.

    len(x):
        Returns the total number of nodes.
    iter(x):
        Returns an iterator of all the stored nodes.

    Attributes
    ----------
    client: :class:`Client`
        The Lavalink client.
    nodes: List[:class:`Node`]
        Cache of all the nodes that Lavalink has created.
    regions: Dict[str, Tuple[str]]
        A mapping of continent -> Discord RTC regions.
    """
    __slots__ = ('_player_queue', '_connect_back', 'client', 'nodes', 'regions')

    def __init__(self, client, regions: Optional[Dict[str, Tuple[str]]], connect_back: bool):
        self._player_queue = []
        self._connect_back: bool = connect_back
        self.client: 'Client' = client
        self.nodes: List[Node] = []
        self.regions: Dict[str, Tuple[str]] = regions or DEFAULT_REGIONS

    def __len__(self) -> int:
        return len(self.nodes)

    def __iter__(self) -> Iterator[Node]:
        yield from self.nodes

    @property
    def available_nodes(self) -> List[Node]:
        """
        Returns a list of available nodes.
        A node is considered available if it has an open WebSocket connection.
        """
        return [n for n in self.nodes if n.available]

    def add_node(self, host: str, port: int, password: str, region: str, name: Optional[str] = None,
                 ssl: bool = False, session_id: Optional[str] = None, connect: bool = True, tags: Optional[Dict[str, Any]] = None) -> Node:
        """
        Adds a node to this node manager.

        Parameters
        ----------
        host: :class:`str`
            The address of the Lavalink node.
        port: :class:`int`
            The port to use for websocket and REST connections.
        password: :class:`str`
            The password used for authentication.
        region: :class:`str`
            The region to assign this node to.
        name: Optional[:class:`str`]
            An identifier for the node that will show in logs. Defaults to ``None``.
        ssl: :class:`bool`
            Whether to use SSL for the node. SSL will use ``wss`` and ``https``, instead of ``ws`` and ``http``,
            respectively. Your node should support SSL if you intend to enable this, either via reverse proxy or
            other methods. Only enable this if you know what you're doing.
        session_id: Optional[:class:`str`]
            The ID of the session to resume. Defaults to ``None``.
            Only specify this if you have the ID of the session you want to resume.
        connect: :class:`bool`
            Whether to immediately connect to the node after creating it.
            If ``False``, you must call :func:`Node.connect` if you require WebSocket functionality.
        tags: Optional[Dict[:class:`str`, Any]]
            Additional tags to attach to this node. You can use this to store additional metadata
            that you may need to access later.

        Returns
        -------
        :class:`Node`
            The created Node instance.
        """
        node = Node(self, host, port, password, region, name, ssl,
                    session_id, connect, tags)
        self.nodes.append(node)
        return node

    def remove_node(self, node: Node):
        """
        Removes a node.

        Make sure you have called :func:`Node.destroy` to close any resources used by this Node.

        .. deprecated:: 5.2.0
            To be consistent with function naming, this method has been deprecated in favour of
            :func:`remove`.

        Parameters
        ----------
        node: :class:`Node`
            The node to remove from the list.
        """
        self.nodes.remove(node)

    def remove(self, node: Node):
        """
        Removes a node.

        Make sure you have called :func:`Node.destroy` to close any resources used by this Node.

        Parameters
        ----------
        node: :class:`Node`
            The node to remove from the list.
        """
        self.nodes.remove(node)

    def get_nodes_by_region(self, region_key: str) -> List[Node]:
        """
        Get a list of nodes by their region.
        This does not account for node availability, so the nodes returned
        could be either available or unavailable.

        Parameters
        ----------
        region_key: :class:`str`
            The region key. If you haven't specified your own regions, this will be
            one of ``asia``, ``eu`` or ``us``, otherwise, it'll be one of the keys
            within the dict you provided.

        Returns
        -------
        List[:class:`Node`]
            A list of nodes. Could be empty if no nodes were found with the specified region key.
        """
        return [n for n in self.nodes if n.region == region_key]

    def get_region(self, endpoint: str) -> Optional[str]:
        """
        Returns a Lavalink.py-friendly region from a Discord voice server address.

        Parameters
        ----------
        endpoint: :class:`str`
            The address of the Discord voice server.

        Returns
        -------
        Optional[:class:`str`]
        """
        if not endpoint:
            return None

        endpoint = endpoint.replace('vip-', '')

        for key in self.regions:
            if not any(n.region == key for n in self.available_nodes):
                continue

            if endpoint.startswith(self.regions[key]):
                return key

        return None

    def find_ideal_node(self, region: Optional[str] = None, exclude: Optional[List[Node]] = None) -> Optional[Node]:
        """
        Finds the best (least used) node in the given region, if applicable.

        Parameters
        ----------
        region: Optional[:class:`str`]
            The region to find a node in. Defaults to ``None``.
        exclude: Optional[List[:class:`Node`]]
            A list of nodes to exclude from the choice.

        Returns
        -------
        Optional[:class:`Node`]
        """
        exclusions = exclude or []
        nodes = None

        if region:
            nodes = [n for n in self.available_nodes if n.region == region and n not in exclusions]

        if not nodes:  # If there are no regional nodes available, or a region wasn't specified.
            nodes = [n for n in self.available_nodes if n not in exclusions]

        if not nodes:
            return None

        best_node = min(nodes, key=lambda node: node.penalty)
        return best_node

    async def _handle_node_ready(self, node: Node):
        player: 'BasePlayer'

        for player in self._player_queue:
            await player.change_node(node)
            last_node = player._original_node or player.node
            last_node_name = last_node.name if last_node else '[no node]'
            _log.debug('Moved player %d from node \'%s\' to node \'%s\'', player.guild_id, last_node_name, node.name)

        if self._connect_back:
            for player in node._original_players:
                await player.change_node(node)
                player._original_node = None

        self._player_queue.clear()

    async def _handle_node_disconnect(self, node: Node):
        """|coro|

        Called when a node is disconnected from Lavalink.

        Parameters
        ----------
        node: :class:`Node`
            The node that has just connected.
        """
        for player in node.players:
            try:
                await player.node_unavailable()
            except:  # noqa: E722 pylint: disable=bare-except
                _log.exception('An error occurred whilst calling player.node_unavailable()')

        best_node = self.find_ideal_node(node.region, exclude=[node])  # Don't use the node these players are moving from.

        if not best_node:
            self._player_queue.extend(node.players)
            _log.warning('Unable to move players, no available nodes! Waiting for a node to become available.')
            return

        # TODO: This may need reinvestigating to make it more robust with the lack of WS requirement.
        # i.e. we need a way to determine whether nodes are "reachable".
        for player in node.players:
            try:
                await player.change_node(best_node)

                if self._connect_back:
                    player._original_node = node
            except ClientError:
                _log.error('Failed to move player %d from node \'%s\' to new node \'%s\'', player.guild_id, node.name, best_node.name)
