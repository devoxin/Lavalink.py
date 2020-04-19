class NodeException(Exception):
    """ Raised when something went wrong with a node. """


class Unauthorized(Exception):
    """ Raised when a REST request fails due to an incorrect password. """


class InvalidTrack(Exception):
    """ Raised when an invalid track was passed. """
