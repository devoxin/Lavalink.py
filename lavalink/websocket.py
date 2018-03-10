import asyncio
import websockets
import json
import logging

log = logging.getLogger(__name__)


class WebSocket:
    def __init__(self, lavalink, host, password, ws_port, ws_retry, shard_count):
        self._lavalink = lavalink

        self._ws = None
        self._queue = []

        self._ws_retry = ws_retry
        self._password = password
        self._host = host
        self._port = ws_port
        self._uri = 'ws://{}:{}'.format(self._host, self._port)
        self._shards = shard_count

        self._shutdown = False

        self._loop = self._lavalink.loop
        self._loop.create_task(self.connect())

    async def connect(self):
        """ Establishes a connection to the Lavalink server """
        await self._lavalink.bot.wait_until_ready()

        if self._ws is not None and self._ws.open:
            log.debug('Websocket still open, closing...')
            await self._ws.close()

        user_id = self._lavalink.bot.user.id
        shard_count = self._lavalink.bot.shard_count or self._shards

        headers = {
            'Authorization': self._password,
            'Num-Shards': shard_count,
            'User-Id': user_id
        }
        log.debug('Preparing to connect to Lavalink')
        log.debug('    with URI: {}'.format(self._uri))
        log.debug('    with headers: {}'.format(str(headers)))
        log.info('Connecting to Lavalink...')

        try:
            self._ws = await websockets.connect(self._uri, extra_headers=headers)
        except OSError:
            log.exception('Failed to connect to Lavalink. ')
        else:
            log.info('Connected to Lavalink!')
            self._loop.create_task(self.listen())
            if self._queue:
                log.info('Replaying {} queued events...'.format(len(self._queue)))
                for task in self._queue:
                    await self.send(**task)

    async def _attempt_reconnect(self) -> bool:
        """
        Attempts to reconnect to the lavalink server.

        Returns
        -------
        bool
            ``True`` if the reconnection attempt was successful.
        """
        log.info('Connection closed; attempting to reconnect in 30 seconds')
        for a in range(0, self._ws_retry):
            await asyncio.sleep(30)
            log.info('Reconnecting... (Attempt {})'.format(a + 1))
            await self.connect()

            if self._ws.open:
                return True
        return False

    async def listen(self):
        while self._shutdown is False:
            try:
                data = json.loads(await self._ws.recv())
            except websockets.ConnectionClosed:
                self._lavalink.players.clear()

                if self._shutdown is True:
                    # Exit gracefully
                    break

                if await self._attempt_reconnect():
                    # self.connect will spawn another listen task, exit cleanly here
                    # without hitting the ws.close() down below.
                    return
                else:
                    log.warning('Unable to reconnect to Lavalink!')
                    # Ensure the ws is closed
                    break

            op = data.get('op', None)
            log.debug('Received websocket data\n' + str(data))

            if not op:
                return log.debug('Received websocket message without op\n' + str(data))

            if op == 'event':
                await self._lavalink.dispatch_event(
                    data['type'], data['guildId'], data.get('reason', data['type'])
                )
            elif op == 'playerUpdate':
                await self._lavalink.update_state(data)

        log.debug("Shutting down web socket.")
        await self._ws.close()

    async def send(self, **data):
        """ Sends data to lavalink """
        if self._ws is not None and self._ws.open:
            log.debug('Sending payload:\n' + str(data))
            await self._ws.send(json.dumps(data))
        else:
            self._queue.append(data)
            log.debug('Websocket not ready; appending payload to queue\n' + str(data))


    def destroy(self):
        self._shutdown = True
