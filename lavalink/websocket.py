import asyncio

import aiohttp

from .events import (TrackEndEvent, TrackExceptionEvent,
                     TrackStuckEvent, WebSocketClosedEvent)
from .stats import Stats
from .utils import decode_track


class WebSocket:
    """ Represents the WebSocket connection with Lavalink. """
    def __init__(self, node, host: str, port: int, password: str, resume_key: str, resume_timeout: int,
                 reconnect_attempts: int):
        self._node = node
        self._lavalink = self._node._manager._lavalink

        self._session = self._lavalink._session
        self._ws = None
        self._message_queue = []

        self._host = host
        self._port = port
        self._password = password
        self._max_reconnect_attempts = reconnect_attempts

        self._resume_key = resume_key
        self._resume_timeout = resume_timeout
        self._resuming_configured = False

        self._user_id = self._lavalink._user_id

        self._closers = (aiohttp.WSMsgType.CLOSE,
                         aiohttp.WSMsgType.CLOSING,
                         aiohttp.WSMsgType.CLOSED)

        asyncio.ensure_future(self.connect())

    @property
    def connected(self):
        """ Returns whether the websocket is connected to Lavalink. """
        return self._ws is not None and not self._ws.closed

    async def connect(self):
        """ Attempts to establish a connection to Lavalink. """
        headers = {
            'Authorization': self._password,
            'User-Id': str(self._user_id),
            'Client-Name': 'Lavalink.py',
            'Num-Shards': '1'  # Legacy header that is no longer used. Here for compatibility.
        }  # soonTM: User-Agent? Also include version in Client-Name as per optional implementation format.

        if self._resuming_configured and self._resume_key:
            headers['Resume-Key'] = self._resume_key

        is_finite_retry = self._max_reconnect_attempts != -1
        max_attempts_str = 'inf' if is_finite_retry else self._max_reconnect_attempts
        attempt = 0

        while not self.connected and (not is_finite_retry or attempt < self._max_reconnect_attempts):
            attempt += 1
            self._lavalink._logger.info('[NODE-{}] Attempting to establish WebSocket '
                                        'connection ({}/{})...'.format(self._node.name, attempt, max_attempts_str))

            try:
                self._ws = await self._session.ws_connect('ws://{}:{}'.format(self._host, self._port), headers=headers,
                                                          heartbeat=60)
            except (aiohttp.ClientConnectorError, aiohttp.WSServerHandshakeError, aiohttp.ServerDisconnectedError) as ce:
                if isinstance(ce, aiohttp.ClientConnectorError):
                    self._lavalink._logger.warning('[NODE-{}] Invalid response received; this may indicate that '
                                                   'Lavalink is not running, or is running on a port different '
                                                   'to the one you passed to `add_node`.'.format(self._node.name))
                elif isinstance(ce, aiohttp.WSServerHandshakeError):
                    if ce.status in (401, 403):  # Special handling for 401/403 (Unauthorized/Forbidden).
                        self._lavalink._logger.warning('[NODE-{}] Authentication failed while trying to '
                                                       'establish a connection to the node.'
                                                       .format(self._node.name))
                        # We shouldn't try to establish any more connections as correcting this particular error
                        # would require the cog to be reloaded (or the bot to be rebooted), so further attempts
                        # would be futile, and a waste of resources.
                        return

                    self._lavalink._logger.warning('[NODE-{}] The remote server returned code {}, '
                                                   'the expected code was 101. This usually '
                                                   'indicates that the remote server is a webserver '
                                                   'and not Lavalink. Check your ports, and try again.'
                                                   .format(self._node.name, ce.status))
                backoff = min(10 * attempt, 60)
                await asyncio.sleep(backoff)
            else:
                await self._node._manager._node_connect(self._node)
                #  asyncio.ensure_future(self._listen())

                if not self._resuming_configured and self._resume_key \
                        and (self._resume_timeout and self._resume_timeout > 0):
                    await self._send(op='configureResuming', key=self._resume_key, timeout=self._resume_timeout)
                    self._resuming_configured = True

                if self._message_queue:
                    for message in self._message_queue:
                        await self._send(**message)

                    self._message_queue.clear()

                await self._listen()
                # Ensure this loop doesn't proceed if _listen returns control back to this function.
                return

        self._lavalink._logger.warning('[NODE-{}] A WebSocket connection could not be established within 3 '
                                       'attempts.'.format(self._node.name))

    async def _listen(self):
        """ Listens for websocket messages. """
        async for msg in self._ws:
            self._lavalink._logger.debug('[NODE-{}] Received WebSocket message: {}'.format(self._node.name, msg.data))

            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._handle_message(msg.json())
            elif msg.type == aiohttp.WSMsgType.ERROR:
                exc = self._ws.exception()
                self._lavalink._logger.error('[NODE-{}] Exception in WebSocket! {}.'.format(self._node.name, exc))
                break
            elif msg.type in self._closers:
                self._lavalink._logger.debug('[NODE-{}] Received close frame with code {}.'.format(self._node.name, msg.data))
                await self._websocket_closed(msg.data, msg.extra)
                return
        await self._websocket_closed()

    async def _websocket_closed(self, code: int = None, reason: str = None):
        """
        Handles when the websocket is closed.

        Parameters
        ----------
        code: :class:`int`
            The response code.
        reason: :class:`str`
            Reason why the websocket was closed. Defaults to `None`
        """
        self._lavalink._logger.debug('[NODE-{}] WebSocket disconnected with the following: code={} '
                                     'reason={}'.format(self._node.name, code, reason))
        self._ws = None
        await self._node._manager._node_disconnect(self._node, code, reason)
        await self.connect()

    async def _handle_message(self, data: dict):
        """
        Handles the response from the websocket.

        Parameters
        ----------
        data: :class:`dict`
            The data given from Lavalink.
        """
        op = data['op']

        if op == 'stats':
            self._node.stats = Stats(self._node, data)
        elif op == 'playerUpdate':
            player = self._lavalink.player_manager.get(int(data['guildId']))

            if not player:
                return

            await player._update_state(data['state'])
        elif op == 'event':
            await self._handle_event(data)
        else:
            self._lavalink._logger.warning('[NODE-{}] Received unknown op: {}'.format(self._node.name, op))

    async def _handle_event(self, data: dict):
        """
        Handles the event from Lavalink.

        Parameters
        ----------
        data: :class:`dict`
            The data given from Lavalink.
        """
        player = self._lavalink.player_manager.get(int(data['guildId']))

        if not player:
            self._lavalink._logger.warning('[NODE-{}] Received event for non-existent player! GuildId: {}'
                                           .format(self._node.name, data['guildId']))
            return

        event_type = data['type']
        event = None

        if event_type == 'TrackEndEvent':
            track = decode_track(data['track'])
            event = TrackEndEvent(player, track, data['reason'])
        elif event_type == 'TrackExceptionEvent':
            event = TrackExceptionEvent(player, player.current, data['error'])
        elif event_type == 'TrackStartEvent':
            pass
        #    event = TrackStartEvent(player, player.current)
        elif event_type == 'TrackStuckEvent':
            event = TrackStuckEvent(player, player.current, data['thresholdMs'])
        elif event_type == 'WebSocketClosedEvent':
            event = WebSocketClosedEvent(player, data['code'], data['reason'], data['byRemote'])
        else:
            self._lavalink._logger.warning('[NODE-{}] Unknown event received: {}'.format(self._node.name, event_type))
            return

        await self._lavalink._dispatch_event(event)

        if player:
            await player._handle_event(event)

    async def _send(self, **data):
        """
        Sends a payload to Lavalink.

        Parameters
        ----------
        data: :class:`dict`
            The data sent to Lavalink.
        """
        if self.connected:
            self._lavalink._logger.debug('[NODE-{}] Sending payload {}'.format(self._node.name, str(data)))
            await self._ws.send_json(data)
        else:
            self._lavalink._logger.debug('[NODE-{}] Send called before WebSocket ready!'.format(self._node.name))
            self._message_queue.append(data)
