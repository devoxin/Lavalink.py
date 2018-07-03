import asyncio
import json
import logging
from datetime import datetime

import websockets

from .Events import TrackStuckEvent, TrackExceptionEvent, TrackEndEvent

log = logging.getLogger(__name__)


class WebSocket:
    def __init__(self, lavalink, host, password, ws_port, ws_retry, shard_count):
        self._lavalink = lavalink
        self.last_response = 0

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
            'User-Id': str(user_id)
        }
        log.debug('Preparing to connect to Lavalink')
        log.debug('    with URI: {}'.format(self._uri))
        log.debug('    with headers: {}'.format(str(headers)))
        log.info('Connecting to Lavalink...')

        try:
            self._ws = await websockets.connect(self._uri, loop=self._loop, extra_headers=headers)
        except OSError as error:
            log.exception('Failed to connect to Lavalink %s', str(error))
        else:
            log.info('Connected to Lavalink!')
            self._loop.create_task(self.listen())
            self._loop.create_task(self._keep_alive())
            if self._queue:
                log.info('Replaying %d queued events...', len(self._queue))
                for task in self._queue:
                    await self.send(**task)

    async def _keep_alive(self):
        """
        Sends a ping to the Lavalink server every 2 seconds
        Experimental fix to attempt to solve issues where nothing is sent via the websocket after a certain amount of time
        """
        while self._shutdown is False:
            try:
                wait_pong = await self._ws.ping()
                await asyncio.wait_for(wait_pong, timeout=5.0)
            except asyncio.TimeoutError:
                log.warning("WS Ping Timeout! Lavalink WS did not respond after 5 seconds.")
                log.warning("Closing WS connection...")
                await self._ws.close()
            except websockets.ConnectionClosed as e:
                while not self._ws.open:
                    await asyncio.sleep(1)
            else:
                self.last_response = datetime.utcnow().timestamp()
            await asyncio.sleep(2)

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
            except websockets.ConnectionClosed as error:
                log.warning('Disconnected from Lavalink %s', str(error))
                for g, p in self._lavalink.players:
                    w = self._lavalink.bot._connection._get_websocket(int(g))
                    await w.voice_state(int(g), None)

                self._lavalink.players.clear()

                if self._shutdown is True:
                    break

                if await self._attempt_reconnect():
                    return
                else:
                    log.warning('Unable to reconnect to Lavalink!')
                    break

            op = data.get('op', None)
            log.debug('Received websocket data %s', str(data))
            self.last_response = datetime.utcnow().timestamp()

            if not op:
                return log.debug('Received websocket message without op %s', str(data))

            if op == 'event':
                log.debug('Received event of type %s', data['type'])
                player = self._lavalink.players[int(data['guildId'])]
                event = None

                if data['type'] == 'TrackEndEvent':
                    event = TrackEndEvent(player, data['track'], data['reason'])
                elif data['type'] == 'TrackExceptionEvent':
                    event = TrackExceptionEvent(player, data['track'], data['error'])
                elif data['type'] == 'TrackStuckEvent':
                    event = TrackStuckEvent(player, data['track'], data['thresholdMs'])

                if event is not None:
                    await self._lavalink.dispatch_event(event)
            elif op == 'playerUpdate':
                await self._lavalink.update_state(data)

        log.debug("Closing Websocket...")
        await self._ws.close()

    async def send(self, **data):
        """ Sends data to lavalink """
        if self._ws is not None and self._ws.open:
            log.debug('Sending payload %s', str(data))
            await self._ws.send(json.dumps(data))
        else:
            self._queue.append(data)
            log.debug('Send called before websocket ready; queueing payload %s', str(data))

    def destroy(self):
        self._shutdown = False
