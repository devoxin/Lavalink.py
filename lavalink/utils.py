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
from typing import Tuple

from .datarw import DataReader
from .models import AudioTrack


def timestamp_to_millis(timestamp: str) -> int:
    """
    Converts a timestamp such as 03:28 or 02:15:53 to milliseconds.

    Example
    -------
    .. code:: python

        await player.play(track, start_time=timestamp_to_millis('01:13'))

    Parameters
    ----------
    timestamp: :class:`str`
        The timestamp to convert into milliseconds.

    Returns
    -------
    :class:`int`
        The millisecond value of the timestamp.
    """
    try:
        sections = list(map(int, timestamp.split(':')))
    except ValueError:
        raise ValueError('Timestamp should consist of integers and colons only')

    if not sections:
        raise TypeError('An invalid timestamp was provided, a timestamp should look like 1:30')

    if len(sections) > 4:
        raise TypeError('Too many segments within the provided timestamp! Provide no more than 4 segments.')

    if len(sections) == 4:
        d, h, m, s = map(int, sections)
        return (d * 86400000) + (h * 3600000) + (m * 60000) + (s * 1000)

    if len(sections) == 3:
        h, m, s = map(int, sections)
        return (h * 3600000) + (m * 60000) + (s * 1000)

    if len(sections) == 2:
        m, s = map(int, sections)
        return (m * 60000) + (s * 1000)

    s, = map(int, sections)
    return s * 1000


def format_time(time: int) -> str:
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


def parse_time(time: int) -> Tuple[int, int, int, int]:
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


def decode_track(track: str) -> AudioTrack:
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
    version = struct.unpack('B', reader.read_byte()) if flags & 1 != 0 else 1

    title = reader.read_utfm()
    author = reader.read_utfm()
    length = reader.read_long()
    identifier = reader.read_utf().decode()
    is_stream = reader.read_boolean()
    uri = reader.read_utf().decode() if reader.read_boolean() else None
    source = reader.read_utf().decode()
    position = reader.read_long()

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

    return AudioTrack(track_object, 0, source=source, position=position, encoder_version=version)


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
