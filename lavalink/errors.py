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
from typing import Optional


class ClientError(Exception):
    """ Raised when something goes wrong within the client. """


class AuthenticationError(Exception):
    """ Raised when a request fails due to invalid authentication. """


class InvalidTrack(Exception):
    """ Raised when an invalid track was passed. """


class LoadError(Exception):
    """ Raised when a track fails to load. E.g. if a DeferredAudioTrack fails to find an equivalent. """


class RequestError(Exception):
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
    """
    __slots__ = ('status', 'timestamp', 'error', 'message', 'path', 'trace')

    def __init__(self, message, status: int, response: dict):
        super().__init__(message)
        self.status: int = status
        self.timestamp: int = response['timestamp']
        self.error: str = response['error']
        self.message: str = response['message']
        self.path: str = response['path']
        self.trace: Optional[str] = response.get('trace', None)
