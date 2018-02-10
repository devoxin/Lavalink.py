import asyncio
import websockets
import json


class WebSocket:
    def __init__(self, lavalink, **kwargs):
        self._lavalink = lavalink
        self.log = self._lavalink.log

        self._ws = None
        self._queue = []

        self._ws_retry = kwargs.pop('ws_retry', 3)
        self._password = kwargs.get('password', '')
        self._host = kwargs.get('host', 'localhost')
        self._port = kwargs.pop('port', 80)
        self._uri = 'ws://{}:{}'.format(self._host, self._port)
        self._shards = self._lavalink.bot.shard_count or kwargs.pop("shard_count", 1)
        self._user_id = self._lavalink.bot.user.id

        self._loop = self._lavalink.bot.loop
        self._loop.create_task(self.connect())

    async def connect(self):
        """ Establishes a connection to the Lavalink server """
        await self._lavalink.bot.wait_until_ready()

        if self._ws and self._ws.open:
            self.log('debug', 'Websocket still open, closing...')
            self._ws.close()

        headers = {
            'Authorization': self._password,
            'Num-Shards': self._shards,
            'User-Id': self._user_id
        }
        self.log('debug', 'Preparing to connect to Lavalink')
        self.log('debug', '    with URI: {}'.format(self._uri))
        self.log('debug', '    with headers: {}'.format(str(headers)))
        self.log('info', 'Connecting to Lavalink...')

        try:
            self._ws = await websockets.connect(self._uri, extra_headers=headers)
        except OSError:
            self.log('error', 'Failed to connect to Lavalink. ')
        else:
            self.log('info', 'Connected to Lavalink!')
            self._loop.create_task(self.listen())
            if self._queue:
                self.log('info', 'Replaying {} queued events...'.format(len(self._queue)))
                for task in self._queue:
                    await self.send(**task)

    async def listen(self):
        try:
            while self._ws.open:
                data = json.loads(await self._ws.recv())
                op = data.get('op', None)
                self.log('debug', 'Received websocket data\n' + str(data))

                if not op:
                    return self.log('debug', 'Received websocket message without op\n' + str(data))

                if op == 'event':
                    await self._lavalink._trigger_event(data['type'], data['guildId'], data.get('reason', 'FINISHED'))
                elif op == 'playerUpdate':
                    await self._lavalink._update_state(data)
        except websockets.ConnectionClosed:
            self._lavalink.bot.lavalink.players.clear()

            self.log('info', 'Connection closed; attempting to reconnect in 30 seconds')
            self._ws.close()
            for a in range(0, self._ws_retry):
                await asyncio.sleep(30)
                self.log('info', 'Reconnecting... (Attempt {})'.format(a + 1))
                await self.connect()

                if self._ws.open:
                    return

            self.log('warn', 'Unable to reconnect to Lavalink!')

    async def send(self, **data):
        """ Sends data to lavalink """
        if not self._ws or not self._ws:
            self._queue.append(data)
            self.log('debug', 'Websocket not ready; appending payload to queue\n' + str(data))
        else:
            self.log('debug', 'Sending payload:\n' + str(data))
            await self._ws.send(json.dumps(data))
