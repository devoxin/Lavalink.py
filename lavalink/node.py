from .events import Event
from .websocket import WebSocket


class Node:
    """
    Represents a Node connection with Lavalink.

    Note
    ----
    Nodes are **NOT** mean't to be added manually, but rather with :func:`Client.add_node`. Doing this can cause
    invalid cache and many more problems.

    Attributes
    ----------
    host: :class:`str`
        The address of the Lavalink node.
    port: :class:`int`
        The port to use for websocket and REST connections.
    password: :class:`str`
        The password used for authentication.
    region: :class:`str`
        The region to assign this node to.
    name: :class:`str`
        The name the :class:`Node` is identified by.
    stats: :class:`Stats`
        The statistics of how the :class:`Node` is performing.
    """
    def __init__(self, manager, host: str, port: int, password: str,
                 region: str, resume_key: str, resume_timeout: int, name: str = None):
        self._manager = manager
        self._ws = WebSocket(self, host, port, password, resume_key, resume_timeout)

        self.host = host
        self.port = port
        self.password = password
        self.region = region
        self.name = name or '{}-{}:{}'.format(self.region, self.host, self.port)
        self.stats = None

    @property
    def available(self):
        """ Returns whether the node is available for requests. """
        return self._ws.connected

    @property
    def _original_players(self):
        """ Returns a list of players that were assigned to this node, but were moved due to failover etc. """
        return [p for p in self._manager._lavalink.player_manager.values() if p._original_node == self]

    @property
    def players(self):
        """ Returns a list of all players on this node. """
        return [p for p in self._manager._lavalink.player_manager.values() if p.node == self]

    @property
    def penalty(self):
        """ Returns the load-balancing penalty for this node. """
        if not self.available or not self.stats:
            return 9e30

        return self.stats.penalty.total

    async def get_tracks(self, query: str):
        """
        Gets all tracks associated with the given query.

        Parameters
        ----------
        query: :class:`str`
            The query to perform a search for.
        """
        return await self._manager._lavalink.get_tracks(query, self)

    async def _dispatch_event(self, event: Event):
        """
        Dispatches the given event to all registered hooks.

        Parameters
        ----------
        event: :class:`Event`
            The event to dispatch to the hooks.
        """
        await self._manager._lavalink._dispatch_event(event)

    async def _send(self, **data):
        """
        Sends the passed data to the node via the websocket connection.

        Parameters
        ----------
        data: any
            The dict to send to Lavalink.
        """
        await self._ws._send(**data)

    def __repr__(self):
        return '<Node name={0.name} region={0.region}>'.format(self)
