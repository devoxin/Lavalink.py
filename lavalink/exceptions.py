class NodeError(Exception):
    """ Raised when something went wrong with a node. """


class AuthenticationError(Exception):
    """ Raised when a request fails due to invalid authentication. """


class InvalidTrack(Exception):
    """ Raised when an invalid track was passed. """
