import asyncio
import logging
import aiohttp
from .stats import Stats
from .events import TrackEndEvent, TrackExceptionEvent, TrackStuckEvent

log = logging.getLogger('lavalink')


class WebSocket:
    def __init__(self, node, host: str, port: int, password: str):
        self._node = node
        self._lavalink = self._node._manager._lavalink

        self._session = self._lavalink._session
        self._ws = None
        self._message_queue = []

        self._host = host
        self._port = port
        self._password = password

        self._shards = self._lavalink._shard_count
        self._user_id = self._lavalink._user_id

        self._closers = [aiohttp.WSMsgType.close,
                         aiohttp.WSMsgType.closing,
                         aiohttp.WSMsgType.closed]

        self._loop = self._lavalink._loop
        asyncio.ensure_future(self.connect())

    @property
    def connected(self):
        """ Returns whether the websocket is connected to Lavalink. """
        return self._ws is not None and not self._ws.closed

    async def connect(self):
        """ Attempts to establish a connection to Lavalink. """
        headers = {
            'Authorization': self._password,
            'Num-Shards': self._shards,
            'User-Id': str(self._user_id)
        }

        attempt = 0

        while not self.connected:
            attempt += 1

            try:
                self._ws = await self._session.ws_connect('ws://{}:{}'.format(self._host, self._port), headers=headers)
            except aiohttp.ClientConnectorError:
                if attempt == 1:
                    log.warning('Failed to connect to node `{}`!'.format(self._node.name))

                backoff = min(10 * attempt, 60)
                await asyncio.sleep(backoff)
            else:
                await self._node._manager._node_connect(self._node)
                asyncio.ensure_future(self._listen())

    async def _listen(self):
        async for msg in self._ws:
            log.debug('Received websocket message from node `{}`: {}'.format(self._node.name, msg.data))

            if msg.type == aiohttp.WSMsgType.text:
                await self._handle_message(msg.json())
            elif msg.type in self._closers:
                await self._websocket_closed(msg.data, msg.extra)
                return
        await self._websocket_closed()

    async def _websocket_closed(self, code: int = None, reason: str = None):
        self._ws = None
        await self._node._manager._node_disconnect(self._node, code, reason)
        await self.connect()

    async def _handle_message(self, data: dict):
        op = data['op']

        if op == 'stats':
            self._node.stats = Stats(self._node, data)
        elif op == 'playerUpdate':
            player = self._lavalink.players.get(int(data['guildId']))

            if not player:
                return

            await player.update_state(data['state'])
        elif op == 'event':
            await self._handle_event(data)
        else:
            log.warning('Received unknown op: {}'.format(op))

    async def _handle_event(self, data: dict):
        player = self._lavalink.players.get(int(data['guildId']))

        if not player:
            return

        event_type = data['type']
        event = None

        if event_type == 'TrackEndEvent':
            event = TrackEndEvent(player, player.current, data['reason'])
        elif event_type == 'TrackStuckEvent':
            event = TrackStuckEvent(player, player.current, data['thresholdMs'])
        elif event_type == 'TrackExceptionEvent':
            event = TrackExceptionEvent(player, player.current, data['error'])
        elif event_type == 'WebSocketClosedEvent':
            pass  # TODO: Send new voice update?
        else:
            log.warning('Received unknown event of type {} on node `{}`'.format(event_type, self._node.name))
            return

        if player:
            await player.handle_event(event)

        await self._lavalink._dispatch_event(event)

    async def _send(self, **data):
        if self.connected:
            log.debug('Sending payload {}'.format(str(data)))
            await self._ws.send_json(data)
        else:
            log.debug('Send called node `{}` ready, payload queued: {}'.format(self._node.name, str(data)))
            self._message_queue.append(data)
