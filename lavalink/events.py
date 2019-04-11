class Event:
    """ The base for all Lavalink events. """


class QueueEndEvent(Event):
    """
    This event is dispatched when there are no more songs in the queue.

    Parameters
    ----------
    player: BasePlayer
        The player that has no more songs in queue.
    """
    def __init__(self, player):
        self.player = player


class TrackStuckEvent(Event):
    """
    This event is dispatched when the currently playing track is stuck.

    Parameters
    ----------
    player: BasePlayer
        The player that has the playing track being stuck.
    track: AudioTrack
        The track is stuck from playing.
    threshold: int
        The amount of time the track had while being stuck.
    """
    def __init__(self, player, track, threshold):
        self.player = player
        self.track = track
        self.threshold = threshold


class TrackExceptionEvent(Event):
    """
    This event is dispatched when an exception occurs while playing a track.

    Parameters
    ----------
    player: BasePlayer
        The player that had the exception occur while playing a track.
    track: AudioTrack
        The track that had the exception while playing.
    exception: Exception
        The type of exception that the track had while playing.
    """
    def __init__(self, player, track, exception):
        self.player = player
        self.track = track
        self.exception = exception


class TrackEndEvent(Event):
    """
    This event is dispatched when the player finished playing a track.

    Parameters
    ----------
    player: BasePlayer
        The player that finished playing a track.
    track: AudioTrack
        The track that finished playing.
    reason: str
        The reason why the track stopped playing.
    """
    def __init__(self, player, track, reason):
        self.player = player
        self.track = track
        self.reason = reason


class TrackStartEvent(Event):
    """
    This event is dispatched when the player starts to play a track.

    Parameters
    ----------
    player: BasePlayer
        The player that started to play a track.
    track: AudioTrack
        The track that started playing.
    """
    def __init__(self, player, track):
        self.player = player
        self.track = track


class PlayerUpdateEvent(Event):
    """
    This event is dispatched when the player's progress changes.

    Parameters
    ----------
    player: BasePlayer
        The player that's progress was updated.
    position: int
        The position of the player that was changed to.
    timestamp: int
        The timestamp that the player is currently on.
    """
    def __init__(self, player, position, timestamp):
        self.player = player
        self.position = position
        self.timestamp = timestamp


class NodeDisconnectedEvent(Event):
    """
    This event is dispatched when a node disconnects and becomes unavailable.

    Parameters
    ----------
    node: Node
        The node that was disconnected from.
    code: int
        The status code of the event.
    reason: str
        The reason of why the node was disconnected.
    """
    def __init__(self, node, code, reason):
        self.node = node
        self.code = code
        self.reason = reason


class NodeConnectedEvent(Event):
    """
    This event is dispatched when Lavalink.py successfully connects to a node.

    Parameters
    ----------
    node: Node
        The node that was successfully connected to.
    """
    def __init__(self, node):
        self.node = node


class NodeChangedEvent(Event):
    """
    This event is dispatched when a player changes to another node.
    Keep in mind this event can be dispatched multiple times if a node
    disconnects and the load balancer moves players to a new node.

    Parameters
    ----------
    player: BasePlayer
        The player whose node was changed.
    old_node: Node
        The node the player was moved from.
    new_node: Node
        The node the player was moved to.
    """
    def __init__(self, player, old_node, new_node):
        self.player = player
        self.old_node = old_node
        self.new_node = new_node


class WebSocketClosedEvent(Event):
    """
    This event is dispatched when a audio websocket to Discord
    is closed. This can happen happen for various reasons like an
    expired voice server update.

    Parameters
    ----------
    player: BasePlayer
        The player whose audio websocket was closed.
    code: int
        The node the player was moved from.
    reason: str
        The node the player was moved to.
    by_remote: bool
        If the websocket was closed remotely.
    """
    def __init__(self, player, code, reason, by_remote):
        self.player = player
        self.code = code
        self.reason = reason
        self.by_remote = by_remote
