class QueueEndEvent:
    def __init__(self, player):
        self.player = player


class TrackStuckEvent:
    def __init__(self, player, track):
        self.player = player
        self.track = track


class TrackExceptionEvent:
    def __init__(self, exception, player, track):
        self.exception = exception
        self.player = player
        self.track = track


class TrackEndEvent:
    def __init__(self, reason, player, track):
        self.reason = reason
        self.player = player
        self.track = track


class TrackStartEvent:
    def __init__(self, player, track):
        self.player = player
        self.track = track
