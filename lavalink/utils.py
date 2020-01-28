import struct

from .datareader import DataReader
from .models import AudioTrack


def format_time(time):
    """
    Formats the given time into HH:MM:SS.

    Parameters
    ----------
    time: :class:`int`
        The time in milliseconds.
    """
    hours, remainder = divmod(time / 1000, 3600)
    minutes, seconds = divmod(remainder, 60)

    return '%02d:%02d:%02d' % (hours, minutes, seconds)


def parse_time(time):
    """
    Parses the given time into days, hours, minutes and seconds.
    Useful for formatting time yourself.

    Parameters
    ----------
    time: :class:`int`
        The time in milliseconds.
    """
    days, remainder = divmod(time / 1000, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    return days, hours, minutes, seconds


def decode_track(track):
    """
    Decodes a base64 track string into an AudioTrack object.

    Parameters
    ----------
    track: :class:`str`
        The base64 track string.
    """
    reader = DataReader(track)

    flags = (reader.read_int() & 0xC0000000) >> 30
    version, = struct.unpack('B', reader.read_byte()) if flags & 1 != 0 else 1  # pylint: disable=unused-variable

    title = reader.read_utf().decode()
    author = reader.read_utf().decode()
    length = reader.read_long()
    identifier = reader.read_utf().decode()
    is_stream = reader.read_boolean()
    uri = reader.read_utf().decode() if reader.read_boolean() else None
    source = reader.read_utf().decode()  # noqa: F841 pylint: disable=unused-variable

    track_object = {
        'track': track,
        'info': {
            'title': title,
            'author': author,
            'length': length,
            'identifier': identifier,
            'isStream': is_stream,
            'uri': uri,
            'isSeekable': not is_stream
        }
    }

    return AudioTrack(track_object, 0)
