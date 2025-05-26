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
from typing import TYPE_CHECKING, Any, Dict, Final, Optional, Sequence, Union

from .server import EndReason, Severity

if TYPE_CHECKING:
    from .abc import BasePlayer, DeferredAudioTrack
    from .node import Node
    from .server import AudioTrack

__all__ = (
    "Event",
    "TrackStartEvent",
    "TrackStuckEvent",
    "TrackExceptionEvent",
    "TrackEndEvent",
    "TrackLoadFailedEvent",
    "QueueEndEvent",
    "PlayerUpdateEvent",
    "NodeConnectedEvent",
    "NodeDisconnectedEvent",
    "NodeChangedEvent",
    "NodeReadyEvent",
    "WebSocketClosedEvent",
    "IncomingWebSocketMessage",
    "PlayerErrorEvent",
)


class Event:
    """ The base for all Lavalink events. """


class TrackStartEvent(Event):
    """
    This event is emitted when a track begins playing (e.g. via player.play())

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that started to play a track.
    track: :class:`AudioTrack`
        The track that started playing.
    """
    __slots__ = ('player', 'track')

    def __init__(self, player: 'BasePlayer', track: 'AudioTrack'):
        self.player: Final['BasePlayer'] = player
        self.track: Final['AudioTrack'] = track


class TrackStuckEvent(Event):
    """
    This event is emitted when the currently playing track is stuck (i.e. has not provided any audio).
    This is typically a fault of the track's underlying audio stream, and not Lavalink itself.

    Note
    ----
    You do not need to manually trigger the start of the next track in the queue within
    this event when using the :class:`DefaultPlayer`. This is handled for you.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player associated with the stuck track.
    track: :class:`AudioTrack`
        The stuck track.
    threshold: :class:`int`
        The configured threshold, in milliseconds, after which a track is considered to be stuck
        when no audio frames were provided.
    """
    __slots__ = ('player', 'track', 'threshold')

    def __init__(self, player: 'BasePlayer', track: 'AudioTrack', threshold: int):
        self.player: Final['BasePlayer'] = player
        self.track: Final['AudioTrack'] = track
        self.threshold: Final[int] = threshold


class TrackExceptionEvent(Event):
    """
    This event is emitted when a track encounters an exception during playback.

    Note
    ----
    You do not need to manually trigger the start of the next track in the queue within
    this event when using the :class:`DefaultPlayer`. This is handled for you.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that had the exception occur while playing a track.
    track: :class:`AudioTrack`
        The track that had the exception while playing.
    message: Optional[:class:`str`]
        The exception message.
    severity: :enum:`Severity`
        The severity of the exception.
    cause: :class:`str`
        The cause of the exception.
    cause_stacktrace: :class:`str`
        The stacktrace for the error.
        May be empty if the server has not been updated to support this.
    """
    __slots__ = ('player', 'track', 'message', 'severity', 'cause', 'cause_stacktrace')

    def __init__(self, player: 'BasePlayer', track: 'AudioTrack', message: Optional[str], severity: Severity,
                 cause: str, cause_stacktrace: str):
        self.player: Final['BasePlayer'] = player
        self.track: Final['AudioTrack'] = track
        self.message: Final[Optional[str]] = message
        self.severity: Final[Severity] = severity
        self.cause: Final[str] = cause
        self.cause_stacktrace: Final[str] = cause_stacktrace


class TrackEndEvent(Event):
    """
    This event is emitted when the player finished playing a track.

    Note
    ----
    You do not need to manually trigger the start of the next track in the queue within
    this event when using the :class:`DefaultPlayer`. This is handled for you.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that finished playing a track.
    track: Optional[:class:`AudioTrack`]
        The track that finished playing.
        This could be ``None`` if Lavalink fails to encode the track.
    reason: :class:`EndReason`
        The reason why the track stopped playing.
    """
    __slots__ = ('player', 'track', 'reason')

    def __init__(self, player: 'BasePlayer', track: Optional['AudioTrack'], reason: EndReason):
        self.player: Final['BasePlayer'] = player
        self.track: Final[Optional['AudioTrack']] = track
        self.reason: Final[EndReason] = reason


class TrackLoadFailedEvent(Event):
    """
    This is a custom event, emitted when a deferred audio track fails to
    produce a playable track. The player will not do anything by itself,
    so it is up to you to skip the broken track.

    Note
    ----
    This event will not automatically trigger the start of the next track in the queue,
    so you must ensure that you do this if you want the player to continue playing from the queue.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player responsible for playing the track.
    track: :class:`DeferredAudioTrack`
        The track that failed to produce a playable track.
    original: Optional[:class:`Exception`]
        The original error, emitted by the track.
        This may be ``None`` if the track did not raise an error,
        but rather returned ``None`` in place of a playable track.
    """
    __slots__ = ('player', 'track', 'original')

    def __init__(self, player: 'BasePlayer', track: 'DeferredAudioTrack', original: Optional[Exception]):
        self.player: Final['BasePlayer'] = player
        self.track: Final['DeferredAudioTrack'] = track
        self.original: Final[Optional[Exception]] = original


class QueueEndEvent(Event):
    """
    This is a custom event, emitted by the :class:`DefaultPlayer` when
    there are no more tracks in the queue.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that has no more songs in queue.
    """
    __slots__ = ('player',)

    def __init__(self, player: 'BasePlayer'):
        self.player: Final['BasePlayer'] = player


class PlayerUpdateEvent(Event):
    """
    This event is emitted when a player's progress changes.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that's progress was updated.
    position: :class:`int`
        The track's elapsed playback time in milliseconds.
    timestamp: :class:`int`
        The track's elapsed playback time as an epoch timestamp in milliseconds.
    connected: :class:`bool`
        Whether or not the player is connected to the voice gateway.
    ping: :class:`int`
        The player's voice connection ping.
        This is calculated from the delay between heartbeat & heartbeat ack.
        This will be -1 when the player doesn't have a voice connection.
    """
    __slots__ = ('player', 'position', 'timestamp', 'connected', 'ping')

    def __init__(self, player: 'BasePlayer', raw_state):
        self.player: Final['BasePlayer'] = player
        self.position: Final[int] = raw_state.get('position')
        self.timestamp: Final[int] = raw_state.get('time')
        self.connected: Final[bool] = raw_state.get('connected')
        self.ping: Final[int] = raw_state.get('ping', -1)


class NodeConnectedEvent(Event):
    """
    This is a custom event, emitted when a connection to a Lavalink node is
    successfully established.

    Attributes
    ----------
    node: :class:`Node`
        The node that was successfully connected to.
    """
    __slots__ = ('node',)

    def __init__(self, node: 'Node'):
        self.node: Final['Node'] = node


class NodeDisconnectedEvent(Event):
    """
    This is a custom event, emitted when the connection to a Lavalink node drops
    and becomes unavailable.

    Attributes
    ----------
    node: :class:`Node`
        The node that was disconnected from.
    code: Optional[:class:`int`]
        The status code of the event.
    reason: Optional[:class:`str`]
        The reason of why the node was disconnected.
    """
    __slots__ = ('node', 'code', 'reason')

    def __init__(self, node: 'Node', code: Optional[int], reason: Optional[str]):
        self.node: Final['Node'] = node
        self.code: Final[Optional[int]] = code
        self.reason: Final[Optional[str]] = reason


class NodeChangedEvent(Event):
    """
    This is a custom event, emitted when a player changes to another Lavalink node.
    Keep in mind this event can be emitted multiple times if a node disconnects and
    the load balancer moves players to a new node.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose node was changed.
    old_node: :class:`Node`
        The node the player was moved from.
    new_node: :class:`Node`
        The node the player was moved to.
    """
    __slots__ = ('player', 'old_node', 'new_node')

    def __init__(self, player: 'BasePlayer', old_node: 'Node', new_node: 'Node'):
        self.player: Final['BasePlayer'] = player
        self.old_node: Final['Node'] = old_node
        self.new_node: Final['Node'] = new_node


class NodeReadyEvent(Event):
    """
    This is a custom event, emitted when a node becomes ready.
    A node is considered ready once it receives the "ready" event from the Lavalink server.

    Attributes
    ----------
    node: :class:`Node`
        The node that became ready.
    session_id: :class:`str`
        The ID of the session.
    resumed: :class:`bool`
        Whether the session was resumed. This will be false if a brand new session was created.
    """
    __slots__ = ('node', 'session_id', 'resumed')

    def __init__(self, node: 'Node', session_id: str, resumed: bool):
        self.node: Final['Node'] = node
        self.session_id: Final[str] = session_id
        self.resumed: Final[bool] = resumed


class WebSocketClosedEvent(Event):
    """
    This event is emitted when an audio websocket to Discord is closed. This can happen
    happen for various reasons, an example being when a channel is deleted.

    Refer to the `Discord Developer docs <https://discord.com/developers/docs/topics/opcodes-and-status-codes#voice-voice-close-event-codes>`_
    for a list of close codes and what they mean. This event primarily exists for debug purposes,
    and no special handling of voice connections should take place unless it is absolutely necessary.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player whose audio websocket was closed.
    code: :class:`int`
        The websocket closure code.
    reason: :class:`str`
        The reason for the websocket closure.
    by_remote: :class:`bool`
        Whether the websocket was closed by the remote server.
    """
    __slots__ = ('player', 'code', 'reason', 'by_remote')

    def __init__(self, player: 'BasePlayer', code: int, reason: str, by_remote: bool):
        self.player: Final['BasePlayer'] = player
        self.code: Final[int] = code
        self.reason: Final[str] = reason
        self.by_remote: Final[bool] = by_remote


class IncomingWebSocketMessage(Event):
    """
    This event is emitted whenever the client receives a websocket message from the Lavalink server.

    You can use this to extend the functionality of the client, particularly useful when used with
    Lavalink server plugins that can add new HTTP routes or websocket messages.

    Attributes
    ----------
    data: Union[Dict[Any, Any], Sequence[Any]]
        The received JSON-formatted data from the websocket.
    node: :class:`Node`
        The node responsible for this websocket message.
    """
    __slots__ = ('data', 'node')

    def __init__(self, data, node: 'Node'):
        self.data: Final[Union[Dict[Any, Any], Sequence[Any]]] = data
        self.node: Final['Node'] = node


class PlayerErrorEvent(Event):
    """
    Raised when an error occurs within a :class:`BasePlayer`.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player in which the error occurred.
    original: :class:`Exception`
        The original error.
    """
    __slots__ = ('player', 'original')

    def __init__(self, player, original):
        self.player: Final['BasePlayer'] = player
        self.original: Final[Exception] = original
        # TODO: Perhaps an enum denoting which area of the player encountered an exception, e.g. ErrorType.PLAY.
