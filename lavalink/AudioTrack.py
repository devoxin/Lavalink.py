class InvalidTrack(Exception):
    """ This exception will be raised when an invalid track was passed. """
    pass


class TrackNotBuilt(Exception):
    """ This exception will be raised when AudioTrack objects hasn't been built. """
    pass


class AudioTrack:
    __slots__ = ('track', 'identifier', 'can_seek', 'author', 'duration', 'stream', 'title', 'uri', 'requester',
                 'preferences')

    def __init__(self, requester, **kwargs):
        self.requester = requester
        self.preferences = kwargs

    @classmethod
    def build(cls, track, requester, **kwargs):
        """ Returns an optional AudioTrack. """
        new_track = cls(requester, **kwargs)
        try:
            new_track.track = track['track']
            new_track.identifier = track['info']['identifier']
            new_track.can_seek = track['info']['isSeekable']
            new_track.author = track['info']['author']
            new_track.duration = track['info']['length']
            new_track.stream = track['info']['isStream']
            new_track.title = track['info']['title']
            new_track.uri = track['info']['uri']

            return new_track
        except KeyError:
            raise InvalidTrack('An invalid track was passed.')

    @property
    def thumbnail(self):
        """ Returns the video thumbnail. Could be an empty string. """
        if not hasattr(self, 'track'):
            raise TrackNotBuilt
        if 'youtube' in self.uri:
            return "https://img.youtube.com/vi/{}/default.jpg".format(self.identifier)

        return ""

    def __repr__(self):
        if not hasattr(self, 'track'):
            raise TrackNotBuilt
        return '<AudioTrack title={0.title} identifier={0.identifier}>'.format(self)
