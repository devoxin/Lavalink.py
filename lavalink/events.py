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


class Event:
    """ The base for all Lavalink events. """


class TrackStartEvent(Event):
    """
    This event is emitted when the player starts to play a track.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that started to play a track.
    track: :class:`AudioTrack`
        The track that started playing.
    """
    __slots__ = ('player', 'track')

    def __init__(self, player, track):
        self.player = player
        self.track = track


class TrackStuckEvent(Event):
    """
    This event is emitted when the currently playing track is stuck.
    This normally has something to do with the stream you are playing
    and not Lavalink itself.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that has the playing track being stuck.
    track: :class:`AudioTrack`
        The track is stuck from playing.
    threshold: :class:`int`
        The amount of time the track had while being stuck.
    """
    __slots__ = ('player', 'track', 'threshold')

    def __init__(self, player, track, threshold):
        self.player = player
        self.track = track
        self.threshold = threshold


class TrackExceptionEvent(Event):
    """
    This event is emitted when an exception occurs while playing a track.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that had the exception occur while playing a track.
    track: :class:`AudioTrack`
        The track that had the exception while playing.
    exception: :class:`str`
        The type of exception that the track had while playing.
    severity: :class:`str`
        The level of severity of the exception.
    """
    __slots__ = ('player', 'track', 'exception', 'severity')

    def __init__(self, player, track, exception, severity):
        self.player = player
        self.track = track
        self.exception = exception
        self.severity = severity


class TrackEndEvent(Event):
    """
    This event is emitted when the player finished playing a track.

    Attributes
    ----------
    player: :class:`BasePlayer`
        The player that finished playing a track.
    track: Optional[:class:`AudioTrack`]
        The track that finished playing.
        This could be ``None`` if Lavalink fails to encode the track.
    reason: :class:`str`
        The reason why the track stopped playing.
    """
    __slots__ = ('player', 'track', 'reason')

    def __init__(self, player, track, reason):
        self.player = player
        self.track = track
        self.reason = reason


class TrackLoadFailedEvent(Event):
    """
    This is a custom event, emitted when a deferred audio track fails to
    produce a playable track. The player will not do anything by itself,
    so it is up to you to skip the broken track.

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

    def __init__(self, player, track, original):
        self.player = player
        self.track = track
        self.original = original


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

    def __init__(self, player):
        self.player = player


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
    """
    __slots__ = ('player', 'position', 'timestamp', 'connected')

    def __init__(self, player, raw_state):
        self.player = player
        self.position = raw_state.get('position')
        self.timestamp = raw_state.get('time')
        self.connected = raw_state.get('connected')


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

    def __init__(self, node):
        self.node = node


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

    def __init__(self, node, code, reason):
        self.node = node
        self.code = code
        self.reason = reason


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

    def __init__(self, player, old_node, new_node):
        self.player = player
        self.old_node = old_node
        self.new_node = new_node


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
        The node the player was moved from.
    reason: :class:`str`
        The node the player was moved to.
    by_remote: :class:`bool`
        If the websocket was closed remotely.
    """
    __slots__ = ('player', 'code', 'reason', 'by_remote')

    def __init__(self, player, code, reason, by_remote):
        self.player = player
        self.code = code
        self.reason = reason
        self.by_remote = by_remote
