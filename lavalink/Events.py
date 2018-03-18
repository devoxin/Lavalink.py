class QueueEndEvent:
    def __init__(self, player):
        self.player = player


class TrackStuckEvent:
    def __init__(self, player, track, threshold):
        self.player = player
        self.track = track
        self.threshold = threshold


class TrackExceptionEvent:
    def __init__(self, player, track, exception):
        self.exception = exception
        self.player = player
        self.track = track


class TrackEndEvent:
    def __init__(self, player, track, reason):
        self.reason = reason
        self.player = player
        self.track = track


class TrackStartEvent:
    def __init__(self, player, track):
        self.player = player
        self.track = track
