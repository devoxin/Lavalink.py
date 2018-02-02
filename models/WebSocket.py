import asyncio
import websockets


class WebSocket:
    def __init__(self, lavalink, **kwargs ws_retry, password, host, port, shards, user_id):
        self.log = self._lavalink.log
        
        self._ws = None
        self._queue = []

        self._lavalink = lavalink
        
        self._ws_retry = kwargs.pop('ws_retry', 3)
        self._password = kwargs.get('password', '')
        self._host = kwargs.get('host', 'localhost')
        self._port = kwargs.pop('port', 80)
        self._uri = 'ws://{}:{}'.format(self._host, self._port)
        self._shards = shards
        self._user_id = user_id

        self._loop = self._lavalink.bot.loop
        self._loop.create_task(self.connect())

    async def connect(self):
        """ Establishes a connection to the Lavalink server """
        await self.lavalink.bot.wait_until_ready()

        if self._ws and self._ws.open:
            self.log('debug', 'Websocket still open, closing...')
            self._ws.close()

        headers = {
            'Authorization': self.password,
            'Num-Shards': self.shards,
            'User-Id': self._user_id
        }
        self.log('verbose', 'Preparing to connect to Lavalink')
        self.log('verbose', '    with URI: {}'.format(self._uri))
        self.log('verbose', '    with headers: {}'.format(str(headers)))
        self.log('info', 'Connecting to Lavalink...')

        try:
            self._ws = await websockets.connect(self._uri, extra_headers=headers)
        except OSError:
            self.log('info', 'Failed to connect to Lavalink. ')
        else:
            self.log('info', 'Connected to Lavalink!')
            self.loop.create_task(self.listen())
            if self._queue:
                self.log('info', 'Replaying {} queued events...'.format(len(self._queue)))
                for task in self._queue:
                    await self.send(**task)

    async def listen(self):
        try:
            while self._ws.open:
                data = json.loads(await self.bot.lavalink.ws.recv())
                op = data.get('op', None)

                if not op:
                    return self.log('debug', 'Received websocket message without op!\n' + str(data))

                if op == 'validationReq':
                    await self._dispatch_join_validator(data)
                elif op == 'isConnectedReq':
                    await self._validate_shard(data)
                elif op == 'sendWS':
                    m = json.loads(data['message'])
                    await self.bot._connection._get_websocket(int(m['d'].get('guild_id', None))).send(data.get('message'))
                elif op == 'event':
                    await self._dispatch_event(data)
                elif op == 'playerUpdate':
                    await self._update_state(data)
