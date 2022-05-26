"""
MIT License

Copyright (c) 2017-present Devoxin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import asyncio

import aiohttp

from .events import (PlayerUpdateEvent, TrackEndEvent, TrackExceptionEvent,
                     TrackStuckEvent, WebSocketClosedEvent)
from .stats import Stats
from .utils import decode_track

CLOSERS = (
    aiohttp.WSMsgType.CLOSE,
    aiohttp.WSMsgType.CLOSING,
    aiohttp.WSMsgType.CLOSED
)


class WebSocket:
    """ Represents the WebSocket connection with Lavalink. """
    def __init__(self, node, host: str, port: int, password: str, ssl: bool, resume_key: str,
                 resume_timeout: int, reconnect_attempts: int):
        self._node = node
        self._lavalink = self._node._manager._lavalink

        self._session = self._lavalink._session
        self._ws = None
        self._message_queue = []

        self._host = host
        self._port = port
        self._password = password
        self._ssl = ssl
        self._max_reconnect_attempts = reconnect_attempts

        self._resume_key = resume_key
        self._resume_timeout = resume_timeout
        self._resuming_configured = False

        asyncio.ensure_future(self.connect())

    @property
    def connected(self):
        """ Returns whether the websocket is connected to Lavalink. """
        return self._ws is not None and not self._ws.closed

    async def close(self, code=aiohttp.WSCloseCode.OK):
        """ Shuts down the websocket connection if there is one. """
        if self._ws:
            await self._ws.close(code=code)
            self._ws = None

    async def connect(self):
        """ Attempts to establish a connection to Lavalink. """
        if self._ws:
            await self.close()

        headers = {
            'Authorization': self._password,
            'User-Id': str(self._lavalink._user_id),
            'Client-Name': 'Lavalink.py',
            'Num-Shards': '1'  # Legacy header that is no longer used. Here for compatibility.
        }
        # TODO: 'User-Agent': 'Lavalink.py/{} (https://github.com/devoxin/lavalink.py)'.format(__version__)

        if self._resuming_configured and self._resume_key:
            headers['Resume-Key'] = self._resume_key

        is_finite_retry = self._max_reconnect_attempts != -1
        max_attempts_str = 'inf' if is_finite_retry else self._max_reconnect_attempts
        attempt = 0

        while not self.connected and (not is_finite_retry or attempt < self._max_reconnect_attempts):
            attempt += 1
            self._lavalink._logger.info('[Node:{}] Attempting to establish WebSocket '
                                        'connection ({}/{})...'.format(self._node.name, attempt, max_attempts_str))

            protocol = 'wss' if self._ssl else 'ws'
            try:
                self._ws = await self._session.ws_connect('{}://{}:{}'.format(protocol, self._host, self._port),
                                                          headers=headers, heartbeat=60)
            except (aiohttp.ClientConnectorError, aiohttp.WSServerHandshakeError, aiohttp.ServerDisconnectedError) as ce:
                if isinstance(ce, aiohttp.ClientConnectorError):
                    self._lavalink._logger.warning('[Node:{}] Invalid response received; this may indicate that '
                                                   'Lavalink is not running, or is running on a port different '
                                                   'to the one you provided to `add_node`.'.format(self._node.name))
                elif isinstance(ce, aiohttp.WSServerHandshakeError):
                    if ce.status in (401, 403):  # Special handling for 401/403 (Unauthorized/Forbidden).
                        self._lavalink._logger.warning('[Node:{}] Authentication failed while trying to '
                                                       'establish a connection to the node.'
                                                       .format(self._node.name))
                        # We shouldn't try to establish any more connections as correcting this particular error
                        # would require the cog to be reloaded (or the bot to be rebooted), so further attempts
                        # would be futile, and a waste of resources.
                        return

                    self._lavalink._logger.warning('[Node:{}] The remote server returned code {}, '
                                                   'the expected code was 101. This usually '
                                                   'indicates that the remote server is a webserver '
                                                   'and not Lavalink. Check your ports, and try again.'
                                                   .format(self._node.name, ce.status))
                else:
                    self._lavalink._logger.exception('[Node:{}] An unknown error occurred whilst trying to establish '
                                                     'a connection to Lavalink'.format(self._node.name))
                backoff = min(10 * attempt, 60)
                await asyncio.sleep(backoff)
            else:
                self._lavalink._logger.info('[Node:{}] WebSocket connection established'.format(self._node.name))
                await self._node._manager._node_connect(self._node)

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

        self._lavalink._logger.warning('[Node:{}] A WebSocket connection could not be established within {} '
                                       'attempts.'.format(self._node.name, max_attempts_str))

    async def _listen(self):
        """ Listens for websocket messages. """
        async for msg in self._ws:
            self._lavalink._logger.debug('[Node:{}] Received WebSocket message: {}'.format(self._node.name, msg.data))

            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._handle_message(msg.json())
            elif msg.type == aiohttp.WSMsgType.ERROR:
                exc = self._ws.exception()
                self._lavalink._logger.error('[Node:{}] Exception in WebSocket! {}.'.format(self._node.name, exc))
                break
            elif msg.type in CLOSERS:
                self._lavalink._logger.debug('[Node:{}] Received close frame with code {}.'.format(self._node.name, msg.data))
                await self._websocket_closed(msg.data, msg.extra)
                return
        await self._websocket_closed(self._ws.close_code, 'AsyncIterator loop exited')

    async def _websocket_closed(self, code: int = None, reason: str = None):
        """
        Handles when the websocket is closed.

        Parameters
        ----------
        code: Optional[:class:`int`]
            The response code.
        reason: Optional[:class:`str`]
            Reason why the websocket was closed. Defaults to ``None``
        """
        self._lavalink._logger.warning('[Node:{}] WebSocket disconnected with the following: code={} '
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
            player_id = data['guildId']
            player = self._lavalink.player_manager.get(int(player_id))

            if not player:
                self._lavalink._logger.debug('[Node:{}] Received playerUpdate for non-existent player! GuildId: {}'
                                             .format(self._node.name, str(data)))
                return

            await player._update_state(data['state'])
            await self._lavalink._dispatch_event(PlayerUpdateEvent(player, data['state']))
        elif op == 'event':
            await self._handle_event(data)
        else:
            self._lavalink._logger.warning('[Node:{}] Received unknown op: {}'.format(self._node.name, op))

    async def _handle_event(self, data: dict):
        """
        Handles the event from Lavalink.

        Parameters
        ----------
        data: :class:`dict`
            The data given from Lavalink.
        """
        player = self._lavalink.player_manager.get(int(data['guildId']))
        event_type = data['type']

        if not player:
            self._lavalink._logger.warning('[Node:{}] Received event type {} for non-existent player! GuildId: {}'
                                           .format(self._node.name, event_type, data['guildId']))
            return

        event = None

        if event_type == 'TrackEndEvent':
            track = decode_track(data['track']) if data['track'] else None
            event = TrackEndEvent(player, track, data['reason'])
        elif event_type == 'TrackExceptionEvent':
            exc_inner = data.get('exception', {})
            exception = data.get('error') or exc_inner.get('cause', 'Unknown exception')
            severity = exc_inner.get('severity', 'UNKNOWN')
            event = TrackExceptionEvent(player, player.current, exception, severity)
        # elif event_type == 'TrackStartEvent':
        #    event = TrackStartEvent(player, player.current)
        elif event_type == 'TrackStuckEvent':
            event = TrackStuckEvent(player, player.current, data['thresholdMs'])
        elif event_type == 'WebSocketClosedEvent':
            event = WebSocketClosedEvent(player, data['code'], data['reason'], data['byRemote'])
        else:
            if event_type == 'TrackStartEvent':
                return

            self._lavalink._logger.warning('[Node:{}] Unknown event received of type \'{}\''.format(self._node.name, event_type))
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
        if not self.connected:
            self._lavalink._logger.debug('[Node:{}] WebSocket not ready; queued outgoing payload'.format(self._node.name))
            self._message_queue.append(data)
            return

        self._lavalink._logger.debug('[Node:{}] Sending payload {}'.format(self._node.name, str(data)))
        try:
            await self._ws.send_json(data)
        except ConnectionResetError:
            self._lavalink._logger.warning('[Node:{}] Failed to send payload due to connection reset!'.format(self._node.name))
