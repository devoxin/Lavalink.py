from .websocket import WebSocket


class Node:
    def __init__(self, lavalink, host: str, port: int, password: str, regions):
        self._lavalink = lavalink
        self.ws = WebSocket(self, host, port, password)

    @property
    def available(self):
        """ Returns whether the node is available for requests """
        return self.ws.connected

    async def get_tracks(self, query: str):
        """ Gets all tracks associated with the given query """
        pass
