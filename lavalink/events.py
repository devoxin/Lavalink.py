class Event:
    """ The base for all Lavalink events. """


class QueueEndEvent(Event):
    """ This event is dispatched when there are no more songs in the queue. """
    def __init__(self, player):
        self.player = player


class TrackStuckEvent(Event):
    """ This event is dispatched when the currently playing song is stuck. """
    def __init__(self, player, track, threshold):
        self.player = player
        self.track = track
        self.threshold = threshold


class TrackExceptionEvent(Event):
    """ This event is dispatched when an exception occurs while playing a track. """
    def __init__(self, player, track, exception):
        self.exception = exception
        self.player = player
        self.track = track


class TrackEndEvent(Event):
    """ This event is dispatched when the player finished playing a track. """
    def __init__(self, player, track, reason):
        self.reason = reason
        self.player = player
        self.track = track


class TrackStartEvent(Event):
    """ This event is dispatched when the player starts to play a track. """
    def __init__(self, player, track):
        self.player = player
        self.track = track


class PlayerUpdateEvent(Event):
    """ This event is dispatched when the player's progress changes """
    def __init__(self, player, position: int, timestamp: int):
        self.player = player
        self.position = position
        self.timestamp = timestamp


class NodeDisconnectedEvent(Event):
    """ This event is dispatched when a node disconnects and becomes unavailable """
    def __init__(self, node, code: int, reason: str):
        self.node = node
        self.code = code
        self.reason = reason


class NodeConnectedEvent(Event):
    """ This event is dispatched when Lavalink.py successfully connects to a node """
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


# TODO: The above needs their parameters documented.
