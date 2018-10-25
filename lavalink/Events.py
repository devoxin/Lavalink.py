class QueueEndEvent:
    """ This event will be dispatched when there are no more songs in the queue. """

    def __init__(self, player):
        self.player = player


class TrackStuckEvent:
    """ This event will be dispatched when the currently playing song is stuck. """

    def __init__(self, player, track, threshold):
        self.player = player
        self.track = track
        self.threshold = threshold


class TrackExceptionEvent:
    """ This event will be dispatched when an exception occurs while playing a track. """

    def __init__(self, player, track, exception):
        self.exception = exception
        self.player = player
        self.track = track


class TrackEndEvent:
    """ This event will be dispatched when the player finished playing a track. """

    def __init__(self, player, track, reason):
        self.reason = reason
        self.player = player
        self.track = track


class TrackStartEvent:
    """ This event will be dispatched when the player starts to play a track. """

    def __init__(self, player, track):
        self.player = player
        self.track = track


class PlayerStatusUpdate:
    """ This event is dispatched every time when lavalink sends a player update. """

    def __init__(self, player, track):
        self.player = player
        self.track = track


class VoiceWebSocketClosedEvent:
    """ This event is dispatched every time Lavalink is disconnected from the Discord WS. """

    def __init__(self, player, code, reason, by_remote):
        self.player = player
        self.code = int(code)
        self.reason = reason
        self.by_remote = by_remote


class StatsUpdateEvent:
    """ This event will be dispatched when the websocket receives a statistics update. """

    def __init__(self, node):
        self.stats = node.stats
        self.node = node


class NodeReadyEvent:
    """ This event will be dispatched when the node is ready for use. """

    def __init__(self, node):
        self.node = node


class NodeDisabledEvent:
    """ This event will be dispatched when the node is removed from service due to an error. """

    def __init__(self, node):
        self.node = node
