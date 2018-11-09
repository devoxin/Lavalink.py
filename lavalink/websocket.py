import asyncio
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
            # TODO: Set node to offline
            self._ws = None
            async with self.session.ws_connect(self._uri, heartbeat=5.0, headers=headers) as ws:
                # TODO: Set node to online
                self._ws = ws
                recon_try = 1
                for entry in self._queue:
                    await ws.send_json(entry)
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.PING:
                        await ws.pong()
                    elif msg.type == aiohttp.WSMsgType.TEXT:
                        data = msg.json()
                        op = data.get('op', None)
                        if op == 'event':
                            pass
                        elif op == 'playerUpdate':
                            pass
                        elif op == 'stats':
                            pass
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        # TODO: Set node to offline
                        self._ws = None
                        break
            await asyncio.sleep(backoff_range[recon_try - 1])
            recon_try += 1

    async def send(self, data):
        if self.connected:
            log.debug('Sending payload {}'.format(str(data)))
            await self._ws.send_json(data)
        else:
            log.debug('Send called before WebSocket ready; queueing payload {}'.format(str(data)))
            self._queue.append(data)

    def destroy(self):
        self._shutdown = True
