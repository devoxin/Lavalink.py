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

from .events import NodeConnectedEvent, NodeDisconnectedEvent
from .node import Node

_log = logging.getLogger(__name__)
DEFAULT_REGIONS = {
    'asia': ('hongkong', 'singapore', 'sydney', 'japan', 'southafrica', 'india'),
    'eu': ('eu', 'amsterdam', 'frankfurt', 'russia', 'london'),
    'us': ('us', 'brazil')
}


class NodeManager:
    """Represents the node manager that contains all lavalink nodes.

    len(x):
        Returns the total number of nodes.
    iter(x):
        Returns an iterator of all the stored nodes.

    Attributes
    ----------
    nodes: :class:`list`
        Cache of all the nodes that Lavalink has created.
    regions: :class:`dict`
        All the regions that Discord supports.
    """
    def __init__(self, lavalink, regions: dict):
        self._lavalink = lavalink
        self._player_queue = []
        self.nodes = []
        self.regions = regions or DEFAULT_REGIONS

    def __len__(self):
        return len(self.nodes)

    def __iter__(self):
        for n in self.nodes:
            yield n

    @property
    def available_nodes(self):
        """ Returns a list of available nodes. """
        return [n for n in self.nodes if n.available]

    def add_node(self, host: str, port: int, password: str, region: str,
                 resume_key: str = None, resume_timeout: int = 60, name: str = None,
                 reconnect_attempts: int = 3, filters: bool = False, ssl: bool = False):
        """
        Adds a node to Lavalink's node manager.

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
        resume_key: Optional[:class:`str`]
            A resume key used for resuming a session upon re-establishing a WebSocket connection to Lavalink.
            Defaults to ``None``.
        resume_timeout: Optional[:class:`int`]
            How long the node should wait for a connection while disconnected before clearing all players.
            Defaults to ``60``.
        name: Optional[:class:`str`]
            An identifier for the node that will show in logs. Defaults to ``None``.
        reconnect_attempts: Optional[:class:`int`]
            The amount of times connection with the node will be reattempted before giving up.
            Set to `-1` for infinite. Defaults to ``3``.
        filters: Optional[:class:`bool`]
            Whether to use the new ``filters`` op. This setting currently only applies to development
            Lavalink builds, where the ``equalizer`` op was swapped out for the broader ``filters`` op which
            offers more than just equalizer functionality. Ideally, you should only change this setting if you
            know what you're doing, as this can prevent the effects from working.
        ssl: Optional[:class:`bool`]
            Whether to use SSL for the node. SSL will use ``wss`` and ``https``, instead of ``ws`` and ``http``,
            respectively. Your node should support SSL if you intend to enable this, either via reverse proxy or
            other methods. Only enable this if you know what you're doing.
        """
        node = Node(self, host, port, password, region, resume_key, resume_timeout, name, reconnect_attempts, filters, ssl)
        self.nodes.append(node)

        _log.info('Added node \'%s\'', node.name)

    def remove_node(self, node: Node):
        """
        Removes a node.

        Make sure you have called :func:`Node.destroy` to close any open WebSocket connection.

        Parameters
        ----------
        node: :class:`Node`
            The node to remove from the list.
        """
        self.nodes.remove(node)
        _log.info('Removed node \'%s\'', node.name)

    def get_region(self, endpoint: str):
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
            nodes = [n for n in self.available_nodes if n.region == key]

            if not nodes:
                continue

            if endpoint.startswith(self.regions[key]):
                return key

        return None

    def find_ideal_node(self, region: str = None):
        """
        Finds the best (least used) node in the given region, if applicable.

        Parameters
        ----------
        region: Optional[:class:`str`]
            The region to find a node in. Defaults to ``None``.

        Returns
        -------
        Optional[:class:`Node`]
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
        """
        Called when a node is connected from Lavalink.

        Parameters
        ----------
        node: :class:`Node`
            The node that has just connected.
        """
        for player in self._player_queue:
            await player.change_node(node)
            original_node_name = player._original_node.name if player._original_node else '[no node]'
            _log.debug('Moved player %d from node \'%s\' to node \'%s\'', player.guild_id, original_node_name, node.name)

        if self._lavalink._connect_back:
            for player in node._original_players:
                await player.change_node(node)
                player._original_node = None

        self._player_queue.clear()
        await self._lavalink._dispatch_event(NodeConnectedEvent(node))

    async def _node_disconnect(self, node: Node, code: int, reason: str):
        """
        Called when a node is disconnected from Lavalink.

        Parameters
        ----------
        node: :class:`Node`
            The node that has just connected.
        code: :class:`int`
            The code for why the node was disconnected.
        reason: :class:`str`
            The reason why the node was disconnected.
        """
        await self._lavalink._dispatch_event(NodeDisconnectedEvent(node, code, reason))

        best_node = self.find_ideal_node(node.region)

        if not best_node:
            self._player_queue.extend(node.players)
            _log.error('Unable to move players, no available nodes! Waiting for a node to become available.')
            return

        for player in node.players:
            await player.change_node(best_node)

            if self._lavalink._connect_back:
                player._original_node = node
