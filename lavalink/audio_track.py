__all__ = ["InvalidTrack", "AudioTrack"]

class InvalidTrack(Exception):
    def __init__(self, message):
        super().__init__(message)


class AudioTrack:
    def __init__(self, track, identifier, can_seek, author, duration, stream,
                 title, uri, requester):
        self.track = track
        self.identifier = identifier
        self.can_seek = can_seek
        self.author = author
        self.duration = duration
        self.stream = stream
        self.title = title
        self.uri = uri
        self.requester = requester

    @classmethod
    def build(cls, track, requester):
        """ Returns an optional AudioTrack """
        try:
            _track = track['track']
            identifier = track['info']['identifier']
            can_seek = track['info']['isSeekable']
            author = track['info']['author']
            duration = track['info']['length']
            stream = track['info']['isStream']
            title = track['info']['title']
            uri = track['info']['uri']
            requester = requester
        except KeyError:
            raise InvalidTrack('an invalid track was passed')

        return cls(_track, identifier, can_seek, author, duration, stream, title,
                   uri, requester)

    @property
    def thumbnail(self):
        """ Returns the video thumbnail. Could be an empty string. """
        if 'youtube' in self.uri:
            return "https://img.youtube.com/vi/{}/default.jpg".format(self.identifier)

        return ""
