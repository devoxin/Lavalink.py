import logging

import aiohttp

log = logging.getLogger(__name__)


class WebSocket:
    def __init__(self, lavalink, node, host, password, port, ws_retry, shard_count):
        self._lavalink = lavalink
        self._node = node

        self.session = None
        self._ws = None
        self._queue = []
        self._ws_retry = ws_retry

        self._password = password
        self._host = host
        self._port = port
        self._uri = 'ws://{}:{}'.format(self._host, self._port)
        self._shards = shard_count
        self._user_id = lavalink.bot.user.id

        self._shutdown = False

        self._loop = self._lavalink.loop
        self._loop.create_task(self.listen())

    @property
    def connected(self):
        """ Returns whether there is a valid WebSocket connection to the Lavalink server or not. """
        return self._ws and not self._ws.closed

    async def listen(self):
        """ Waits to receive a payload from the Lavalink server and processes it. """
        recon_try = 1
        backoff_range = [min(max(x, 3), 30) for x in range(0, self._ws_retry * 5, 5)]
        self.session = aiohttp.ClientSession(loop=self._loop)
        headers = {
            'Authorization': self._password,
            'Num-Shards': self._shards,
            'User-Id': str(self._user_id)
        }
        while not self._shutdown and recon_try < len(backoff_range):
            async with self.session.ws_connect(self._uri, heartbeat=5.0, headers=headers) as ws:
                self._ws = ws
                for entry in self._queue:
                    await ws.send_json(entry)
                async for msg in ws:
                    pass  # TODO: Process message

    def destroy(self):
        self._shutdown = True
