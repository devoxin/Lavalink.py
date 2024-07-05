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
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import aiohttp

from .errors import AuthenticationError, ClientError, RequestError
from .events import (IncomingWebSocketMessage, NodeConnectedEvent,
                     NodeDisconnectedEvent, NodeReadyEvent, PlayerUpdateEvent,
                     TrackEndEvent, TrackExceptionEvent, TrackStartEvent,
                     TrackStuckEvent, WebSocketClosedEvent)
from .server import EndReason, Severity
from .stats import Stats

if TYPE_CHECKING:
    from .abc import BasePlayer
    from .client import Client
    from .node import Node

_log = logging.getLogger(__name__)
CLOSE_TYPES = (
    aiohttp.WSMsgType.CLOSE,
    aiohttp.WSMsgType.CLOSING,
    aiohttp.WSMsgType.CLOSED
)
MESSAGE_QUEUE_MAX_SIZE = 25
LAVALINK_API_VERSION = 'v4'


class Transport:
    """ The class responsible for handling connections to a Lavalink server. """
    __slots__ = ('client', '_node', '_session', '_ws', '_message_queue', 'trace_requests',
                 '_host', '_port', '_password', '_ssl', 'session_id', '_destroyed')

    def __init__(self, node, host: str, port: int, password: str, ssl: bool, session_id: Optional[str], connect: bool = True):
        self.client: 'Client' = node.client
        self._node: 'Node' = node

        self._session: aiohttp.ClientSession = self.client._session
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._message_queue = []
        self.trace_requests = False

        self._host: str = host
        self._port: int = port
        self._password: str = password
        self._ssl: bool = ssl

        self.session_id: Optional[str] = session_id
        self._destroyed: bool = False

        if connect:
            self.connect()

    @property
    def ws_connected(self):
        """ Returns whether the websocket is connected to Lavalink. """
        return self._ws is not None and not self._ws.closed

    @property
    def http_uri(self) -> str:
        """ Returns a 'base' URI pointing to the node's address and port, also factoring in SSL. """
        return f'{"https" if self._ssl else "http"}://{self._host}:{self._port}'

    async def close(self, code=aiohttp.WSCloseCode.OK):
        """|coro|

        Shuts down the websocket connection if there is one.
        """
        if self._ws:
            await self._ws.close(code=code)
            self._ws = None

    def connect(self) -> asyncio.Task:
        """ Attempts to establish a connection to Lavalink. """
        loop = asyncio.get_event_loop()
        return loop.create_task(self._connect())

    async def destroy(self):
        """|coro|

        Closes the WebSocket gracefully, and stops any further reconnecting.
        Useful when needing to remove a node.
        """
        self._destroyed = True
        await self.close()

    async def _connect(self):
        if self._destroyed:
            raise IOError('Cannot instantiate any connections with a closed session!')

        if self._ws:
            await self.close()

        headers = {
            'Authorization': self._password,
            'User-Id': str(self.client._user_id),
            'Client-Name': f'Lavalink.py/{__import__("lavalink").__version__}'
        }

        if self.session_id is not None:
            headers['Session-Id'] = self.session_id

        _log.info('[Node:%s] Establishing WebSocket connection to Lavalink...', self._node.name)

        protocol = 'wss' if self._ssl else 'ws'
        attempt = 0

        while not self.ws_connected and not self._destroyed:
            attempt += 1
            try:
                self._ws = await self._session.ws_connect(f'{protocol}://{self._host}:{self._port}/{LAVALINK_API_VERSION}/websocket',
                                                          headers=headers,
                                                          heartbeat=60)
            except (aiohttp.ClientConnectorError, aiohttp.WSServerHandshakeError, aiohttp.ServerDisconnectedError) as error:
                if isinstance(error, aiohttp.ClientConnectorError):
                    _log.warning('[Node:%s] Invalid response received; is the server running on the correct port?',
                                 self._node.name)
                elif isinstance(error, aiohttp.WSServerHandshakeError):
                    if error.status in (401, 403):  # Special handling for 401/403 (Unauthorized/Forbidden).
                        _log.warning('[Node:%s] Authentication failed while trying to establish a connection to the node.',
                                     self._node.name)
                        # We shouldn't try to establish any more connections as correcting this particular error
                        # would require the cog to be reloaded (or the bot to be rebooted), so further attempts
                        # would be futile, and a waste of resources.
                    else:
                        _log.warning('[Node:%s] Received code \'%d\' (expected \'101\'). Check your server\'s ports and try again.',
                                     self._node.name, error.status)

                    return
                else:
                    _log.exception('[Node:%s] An unknown error occurred whilst trying to establish a connection to Lavalink', self._node.name)

                backoff = min(10 * attempt, 60)
                await asyncio.sleep(backoff)
            else:
                _log.info('[Node:%s] WebSocket connection established', self._node.name)
                await self.client._dispatch_event(NodeConnectedEvent(self._node))

                if self._message_queue:
                    for message in self._message_queue:
                        await self._send(**message)

                    self._message_queue.clear()

                attempt = 0
                await self._listen()

    async def _listen(self):
        """ Listens for websocket messages. """
        close_code: Optional[aiohttp.WSCloseCode] = None
        close_reason: Optional[str] = 'Improper websocket closure'

        assert self._ws is not None

        async for msg in self._ws:
            _log.debug('[Node:%s] Received WebSocket message: %s', self._node.name, msg.data)

            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    await self._handle_message(msg.json())
                except Exception:  # pylint: disable=W0718
                    _log.exception('[Node:%s] Unexpected error occurred whilst processing websocket message', self._node.name)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                exc = self._ws.exception()
                _log.error('[Node:%s] Exception in WebSocket!', self._node.name, exc_info=exc)
                close_code = aiohttp.WSCloseCode.INTERNAL_ERROR
                close_reason = 'WebSocket error'
                break
            elif msg.type in CLOSE_TYPES:
                _log.debug('[Node:%s] Received close frame with code %d.', self._node.name, msg.data)
                close_code = msg.data
                close_reason = msg.extra
                break

        ws_close_code = self._ws.close_code

        if close_code is None and ws_close_code is not None:
            close_code = aiohttp.WSCloseCode(ws_close_code)

        await self.close(close_code or aiohttp.WSCloseCode.ABNORMAL_CLOSURE)
        await self._websocket_closed(close_code, close_reason)

    async def _websocket_closed(self, code: Optional[int] = None, reason: Optional[str] = None):
        """
        Handles when the websocket is closed.

        Parameters
        ----------
        code: Optional[:class:`int`]
            The response code.
        reason: Optional[:class:`str`]
            Reason why the websocket was closed. Defaults to ``None``.
        """
        _log.warning('[Node:%s] WebSocket disconnected with the following: code=%s reason=%s', self._node.name, code, reason)
        self._ws = None
        await self._node.manager._handle_node_disconnect(self._node)
        await self.client._dispatch_event(NodeDisconnectedEvent(self._node, code, reason))

    async def _handle_message(self, data: Union[Dict[Any, Any], List[Any]]):
        """
        Handles the response from the websocket.

        Parameters
        ----------
        data: Union[Dict[Any, Any], List[Any]]
            The payload received from the Lavalink server.
        """
        if self.client.has_listeners(IncomingWebSocketMessage):
            await self.client._dispatch_event(IncomingWebSocketMessage(data.copy(), self._node))

        if not isinstance(data, dict) or 'op' not in data:
            return

        op = data['op']  # pylint: disable=C0103

        if op == 'ready':
            self.session_id = data['sessionId']
            await self._node.manager._handle_node_ready(self._node)
            await self.client._dispatch_event(NodeReadyEvent(self._node, data['sessionId'], data['resumed']))
        elif op == 'playerUpdate':
            guild_id = int(data['guildId'])
            player: 'BasePlayer' = self.client.player_manager.get(guild_id)  # type: ignore

            if not player:
                _log.debug('[Node:%s] Received playerUpdate for non-existent player! GuildId: %d', self._node.name, guild_id)
                return

            if player.node != self._node:
                _log.debug('[Node:%s] Received playerUpdate for a player that doesn\'t belong to this node (player is moving?) GuildId: %d',
                           self._node.name, guild_id)
                return

            state = data['state']
            await player.update_state(state)
            await self.client._dispatch_event(PlayerUpdateEvent(player, state))
        elif op == 'stats':
            self._node.stats = Stats(self._node, data)
        elif op == 'event':
            await self._handle_event(data)
        else:
            _log.warning('[Node:%s] Received unknown op: %s', self._node.name, op)

    async def _handle_event(self, data: dict):
        """
        Handles the event from Lavalink.

        Parameters
        ----------
        data: :class:`dict`
            The data given from Lavalink.
        """
        player: 'BasePlayer' = self.client.player_manager.get(int(data['guildId']))  # type: ignore
        event_type = data['type']

        if not player:
            if event_type not in ('TrackEndEvent', 'WebSocketClosedEvent'):  # Player was most likely destroyed if it's any of these.
                _log.warning('[Node:%s] Received event type %s for non-existent player! GuildId: %s', self._node.name, event_type, data['guildId'])

            return

        event = None

        if event_type == 'TrackStartEvent':  # Always fired after track end event (for previous track), and before any track exception/stuck events.
            if player._next is not None:
                player.current = player._next
                player._next = None

            assert player.current is not None
            event = TrackStartEvent(player, player.current)

            if hasattr(player, '_internal_pause'):
                player._internal_pause = False  # type: ignore
        elif event_type == 'TrackEndEvent':
            end_reason = EndReason.from_str(data['reason'])
            event = TrackEndEvent(player, player.current, end_reason)
        elif event_type == 'TrackExceptionEvent':
            exception = data['exception']
            message = exception['message']
            severity = Severity.from_str(exception['severity'])
            cause = exception['cause']

            assert player.current is not None
            event = TrackExceptionEvent(player, player.current, message, severity, cause)
        elif event_type == 'TrackStuckEvent':
            assert player.current is not None
            event = TrackStuckEvent(player, player.current, data['thresholdMs'])
        elif event_type == 'WebSocketClosedEvent':
            event = WebSocketClosedEvent(player, data['code'], data['reason'], data['byRemote'])
        else:
            if not self.client.has_listeners(IncomingWebSocketMessage):
                _log.warning('[Node:%s] Unknown event received of type \'%s\'', self._node.name, event_type)
            return

        await self.client._dispatch_event(event)

        if player:
            try:
                await player.handle_event(event)
            except:  # noqa: E722 pylint: disable=bare-except
                _log.exception('Player %d encountered an error whilst handling event %s', player.guild_id, type(event).__name__)

    async def _send(self, **data):
        """
        Sends a payload to Lavalink.

        Parameters
        ----------
        data: :class:`dict`
            The data sent to Lavalink.
        """
        if not self.ws_connected:
            _log.debug('[Node:%s] WebSocket not ready; queued outgoing payload.', self._node.name)

            if len(self._message_queue) >= MESSAGE_QUEUE_MAX_SIZE:
                _log.warning('[Node:%s] WebSocket message queue is currently at capacity, discarding payload.', self._node.name)
            else:
                self._message_queue.append(data)

            return

        _log.debug('[Node:%s] Sending payload %s', self._node.name, str(data))
        assert self._ws is not None  # This should always pass as self.ws_connected returns False if the ws does not exist.

        try:
            await self._ws.send_json(data)
        except ConnectionResetError:
            _log.warning('[Node:%s] Failed to send payload due to connection reset!', self._node.name)

    async def _request(self, method: str, path: str, to=None, trace: bool = False, versioned: bool = True, **kwargs):  # pylint: disable=C0103
        if self._destroyed:
            raise IOError('Cannot instantiate any connections with a closed session!')

        if trace is True or self.trace_requests is True:
            kwargs['params'] = {**kwargs.get('params', {}), 'trace': 'true'}

        if path.startswith('/'):
            path = path[1:]

        if versioned:
            request_url = f'{self.http_uri}/{LAVALINK_API_VERSION}/{path}'
        else:
            request_url = f'{self.http_uri}/{path}'

        _log.debug('[Node:%s] Sending request to Lavalink with the following parameters: method=%s, url=%s, params=%s, json=%s',
                   self._node.name, method, request_url, kwargs.get('params', {}), kwargs.get('json', {}))

        try:
            async with self._session.request(method=method, url=request_url,
                                             headers={'Authorization': self._password}, **kwargs) as res:
                if res.status in (401, 403):
                    raise AuthenticationError

                if res.status == 200:
                    if to is str:
                        return await res.text()

                    json = await res.json()
                    return json if to is None else to.from_dict(json)

                if res.status == 204:
                    return True

                raise RequestError('An invalid response was received from the node.',
                                   status=res.status, response=await res.json(), params=kwargs.get('params', {}))
        except (AuthenticationError, RequestError, asyncio.TimeoutError, aiohttp.ClientError):
            raise  # Pass the caught errors back to the caller in their 'original' form.
        except Exception as original:
            raise ClientError from original
