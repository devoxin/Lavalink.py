"""
MIT License

Copyright (c) 2017-present Devoxin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import struct

from .datarw import DataReader
from .models import AudioTrack


def format_time(time):
    """
    Formats the given time into HH:MM:SS.

    Parameters
    ----------
    time: :class:`int`
        The time in milliseconds.

    Returns
    -------
    :class:`str`
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

    Returns
    -------
    Tuple[:class:`int`, :class:`int`, :class:`int`, :class:`int`]
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

    Returns
    -------
    :class:`AudioTrack`
    """
    reader = DataReader(track)

    flags = (reader.read_int() & 0xC0000000) >> 30
    version = struct.unpack('B', reader.read_byte()) if flags & 1 != 0 else 1  # noqa: F841 pylint: disable=unused-variable

    title = reader.read_utfm()
    author = reader.read_utfm()
    length = reader.read_long()
    identifier = reader.read_utf().decode()
    is_stream = reader.read_boolean()
    uri = reader.read_utf().decode() if reader.read_boolean() else None
    source = reader.read_utf().decode()
    position = reader.read_long()  # noqa: F841 pylint: disable=unused-variable

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

    return AudioTrack(track_object, 0, source=source)


# def encode_track(track: dict):
#     assert {'title', 'author', 'length', 'identifier', 'is_stream', 'uri', 'source', 'position'} == track.keys()

#     writer = DataWriter()

#     version = struct.pack('B', 2)
#     writer.write_byte(version)
#     writer.write_utf(track['title'])
#     writer.write_utf(track['author'])
#     writer.write_long(track['length'])
#     writer.write_utf(track['identifier'])
#     writer.write_boolean(track['is_stream'])
#     writer.write_boolean(track['uri'])
#     writer.write_utf(track['uri'])
#     writer.write_utf(track['source'])
#     writer.write_long(track['position'])

#     enc = writer.finish()
#     b64 = b64encode(enc)
#     return b64
