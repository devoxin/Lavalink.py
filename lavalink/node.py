from .websocket import WebSocket


class Node:
    def __init__(self, lavalink, host: str, port: int, password: str, regions):
        self._lavalink = lavalink
        self._ws = WebSocket(self, host, port, password)

        self.host = host
        self.port = port
        self.password = password

    @property
    def available(self):
        """ Returns whether the node is available for requests """
        return self._ws.connected

    async def get_tracks(self, query: str):
        """ Gets all tracks associated with the given query """
        return await self._lavalink.get_tracks(query, self)

    async def _send(self, **data):
        """ wrapper around ws.send """  # TODO: Change
        await self._ws._send(**data)
