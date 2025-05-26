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
from typing import TYPE_CHECKING, Any, Dict, Final, Optional

if TYPE_CHECKING:
    from .node import Node

__all__ = (
    "LavalinkError",
    "ClientError",
    "AuthenticationError",
    "InvalidTrack",
    "LoadError",
    "RequestError",
)


class LavalinkError(Exception):
    """ Base exception for all errors raised by Lavalink.py. """


class ClientError(LavalinkError):
    """ Raised when something goes wrong within the client. """


class AuthenticationError(LavalinkError):
    """ Raised when a request fails due to invalid authentication. """


class InvalidTrack(LavalinkError):
    """ Raised when an invalid track was passed. """


class LoadError(LavalinkError):
    """ Raised when a track fails to load. E.g. if a DeferredAudioTrack fails to find an equivalent. """


class RequestError(LavalinkError):
    """
    Raised when a request to the Lavalink server fails.

    Attributes
    ----------
    status: :class:`int`
        The HTTP status code returned by the server.
    timestamp: :class:`int`
        The epoch timestamp in milliseconds, at which the error occurred.
    error: :class:`str`
        The HTTP status code message.
    message: :class:`str`
        The error message.
    path: :class:`str`
        The request path.
    trace: Optional[:class:`str`]
        The stack trace of the error. This will only be present if ``trace=true`` was provided
        in the query parameters of the request.
    params: Dict[str, Any]
        The parameters passed to the request that errored.
    """
    __slots__ = ('node', 'status', 'timestamp', 'error', 'message', 'path', 'trace', 'params')

    def __init__(self, node: 'Node', status: int, response: dict, params: Dict[str, Any]):
        self.node: Final['Node'] = node
        self.status: Final[int] = status
        self.timestamp: Final[int] = response['timestamp']
        self.error: Final[str] = response['error']
        self.message: Final[str] = response.get('message', '')
        self.path: Final[str] = response['path']
        self.trace: Final[Optional[str]] = response.get('trace', None)
        self.params: Final[Dict[str, Any]] = params
        super().__init__(f'An error occurred during a request to the node ({self.message}): {self.error}')
