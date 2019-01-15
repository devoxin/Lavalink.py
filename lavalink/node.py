import logging
from .websocket import WebSocket
from .events import Event

log = logging.getLogger('lavalink')


class Node:
    def __init__(self, manager, host: str, port: int, password: str, region: str, name: str, resume_key: str, resume_timeout: int):
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
    def players(self):
        """ Returns a list of all players on this node """
        return [p for p in self._manager._lavalink.players.values() if p.node == self]

    @property
    def penalty(self):
        """ Returns the load-balancing penalty for this node """
        if not self.available or not self.stats:
            return 9e30

        return self.stats.penalty.total

    async def get_tracks(self, query: str):
        """
        Gets all tracks associated with the given query.
        ----------
        :param query:
            The query to perform a search for.
        """
        return await self._manager._lavalink.get_tracks(query, self)

    async def _dispatch_event(self, event: Event):
        """
        Dispatches the given event to all registered hooks
        ----------
        :param event:
            The event to dispatch to the hooks
        """
        await self._manager._lavalink._dispatch_event(event)

    async def _send(self, **data):
        """
        Sends the given data this node's websocket connection.
        ----------
        :param data:
            The dict to send to Lavalink.
        """
        await self._ws._send(**data)

    def __repr__(self):
        return '<Node name={0.name} region={0.region}>'.format(self)
