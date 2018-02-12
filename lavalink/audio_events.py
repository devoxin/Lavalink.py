from abc import ABC, abstractmethod
from collections import deque


class Event(ABC):
    @abstractmethod
    def __init__(self, player):
        self.player = player


class TrackPauseEvent(Event):
    def __init__(self, player):
        super().__init__(player)


class TrackResumeEvent(Event):
    def __init__(self, player):
        super().__init__(player)


class TrackStartEvent(Event):
    def __init__(self, player, track):
        super().__init__(player)
        self.track = track


class TrackEndEvent(Event):
    def __init__(self, player, track, reason):
        super().__init__(player)
        self.track = track
        self.reason = reason


class TrackExceptionEvent(Event):
    def __init__(self, player, track, exception):
        super().__init__(player)
        self.track = track
        self.exception = exception


class TrackStuckEvent(Event):
    def __init__(self, player, track, threshold_ms):
        super().__init__(player)
        self.track = track
        self.threshold_ms = threshold_ms


class AbstractPlayerEventAdapter(ABC):
    def __init__(self, player, *args, **kwargs):
        self.player = player

    @abstractmethod
    async def track_pause(self, event: TrackPauseEvent):
        pass

    @abstractmethod
    async def track_resume(self, event: TrackResumeEvent):
        pass

    @abstractmethod
    async def track_start(self, event: TrackStartEvent):
        pass

    @abstractmethod
    async def track_end(self, event: TrackEndEvent):
        pass

    @abstractmethod
    async def track_exception(self, event: TrackExceptionEvent):
        pass

    @abstractmethod
    async def track_stuck(self, event: TrackStuckEvent):
        pass

    async def on_event(self, event):
        if not issubclass(event.__class__, Event):
            raise TypeError
        if isinstance(event.__class__, TrackPauseEvent):
            self.track_pause(event)
        elif isinstance(event.__class__, TrackResumeEvent):
            self.track_resume(event)
        elif isinstance(event.__class__, TrackStartEvent):
            self.track_start(event)
        elif isinstance(event.__class__, TrackEndEvent):
            self.track_end(event)
        elif isinstance(event.__class__, TrackExceptionEvent):
            self.track_exception(event)
        elif isinstance(event.__class__, TrackStuckEvent):
            self.track_stuck(event)


class DefaultEventAdapter(AbstractPlayerEventAdapter):
    """
    The default event adapter
    TODO: Add more shit to this class
    """
    def __init__(self, player, ctx):
        super().__init__(player)
        self.ctx = ctx
        self.bot = ctx.bot
        self.queue = deque()

    def track_resume(self, event: TrackResumeEvent):
        pass

    def track_exception(self, event: TrackExceptionEvent):
        pass

    def track_start(self, event: TrackStartEvent):
        pass

    def track_pause(self, event: TrackPauseEvent):
        pass

    def track_end(self, event: TrackEndEvent):
        pass

    def track_stuck(self, event: TrackStuckEvent):
        pass

