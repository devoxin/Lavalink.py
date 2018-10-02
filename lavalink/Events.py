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


class StatsUpdateEvent:
    """ This event will be dispatched when the websocket receives a statistics update. """
    def __init__(self, data):
        self.stats = data
