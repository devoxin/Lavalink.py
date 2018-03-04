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

        self._loop = self._lavalink.loop
        self._loop.create_task(self.connect())

    async def connect(self):
        """ Establishes a connection to the Lavalink server """
        await self._lavalink.bot.wait_until_ready()

        if self._ws and self._ws.open:
            log.debug('Websocket still open, closing...')
            self._ws.close()

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

    async def listen(self):
        try:
            while self._ws.open:
                data = json.loads(await self._ws.recv())
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
        except websockets.ConnectionClosed:
            self._lavalink.players.clear()

            log.info('Connection closed; attempting to reconnect in 30 seconds')
            self._ws.close()
            for a in range(0, self._ws_retry):
                await asyncio.sleep(30)
                log.info('Reconnecting... (Attempt {})'.format(a + 1))
                await self.connect()

                if self._ws.open:
                    return

            log.warning('Unable to reconnect to Lavalink!')

    async def send(self, **data):
        """ Sends data to lavalink """
        if not self._ws or not self._ws:
            self._queue.append(data)
            log.debug('Websocket not ready; appending payload to queue\n' + str(data))
        else:
            log.debug('Sending payload:\n' + str(data))
            await self._ws.send(json.dumps(data))
