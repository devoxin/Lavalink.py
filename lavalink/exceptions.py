class NodeException(Exception):
    """ The exception will be raised when something went wrong with a node. """


class InvalidTrack(Exception):
    """ This exception will be raised when an invalid track was passed. """


class TrackNotBuilt(Exception):
    """ This exception will be raised when AudioTrack objects hasn't been built. """
