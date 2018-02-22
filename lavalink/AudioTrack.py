class InvalidTrack(Exception):
    def __init__(self, message):
        super().__init__(message)


class AudioTrack:
    def build(self, track, requester):
        """ Returns an optional AudioTrack """
        try:
            self.track = track['track']
            self.identifier = track['info']['identifier']
            self.can_seek = track['info']['isSeekable']
            self.author = track['info']['author']
            self.duration = track['info']['length']
            self.stream = track['info']['isStream']
            self.title = track['info']['title']
            self.uri = track['info']['uri']
            self.requester = requester

            return self
        except KeyError:
            raise InvalidTrack('an invalid track was passed')

    @property
    def thumbnail(self):
        """ Returns the video thumbnail. Could be an empty string. """
        if 'youtube' in self.uri:
            return "https://img.youtube.com/vi/{}/default.jpg".format(self.identifier)

        return ""
