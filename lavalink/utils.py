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
from base64 import b64encode
from typing import Dict, Optional, Tuple, Union

from .dataio import DataReader, DataWriter
from .errors import InvalidTrack
from .player import AudioTrack

V2_KEYSET = {'title', 'author', 'length', 'identifier', 'isStream', 'uri', 'sourceName', 'position'}
V3_KEYSET = {'title', 'author', 'length', 'identifier', 'isStream', 'uri', 'artworkUrl', 'isrc', 'sourceName', 'position'}


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
    except ValueError as ve:
        raise ValueError('Timestamp should consist of integers and colons only') from ve

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

    return f'{hours:02}:{minutes:02}:{seconds:02}'


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


def _read_track_common(reader: DataReader) -> Tuple[str, str, int, str, bool, Optional[str]]:
    """
    Reads common fields between v1-3 AudioTracks.

    Returns
    -------
    Tuple[str, str, int, str, bool, Optional[str]]
        A tuple containing (title, author, length, identifier, isStream, uri) fields.
    """
    title = reader.read_utfm()
    author = reader.read_utfm()
    length = reader.read_long()
    identifier = reader.read_utf().decode()
    is_stream = reader.read_boolean()
    uri = reader.read_nullable_utf()
    return (title, author, length, identifier, is_stream, uri)


def _write_track_common(track: Dict[str, Union[Optional[str], bool, int]], writer: DataWriter):
    writer.write_utf(track['title'])
    writer.write_utf(track['author'])
    writer.write_long(track['length'])
    writer.write_utf(track['identifier'])
    writer.write_boolean(track['isStream'])
    writer.write_nullable_utf(track['uri'])


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
    version, = struct.unpack('B', reader.read_byte()) if flags & 1 != 0 else 1

    title, author, length, identifier, is_stream, uri = _read_track_common(reader)
    extra_fields = {}

    if version == 3:
        extra_fields['artworkUrl'] = reader.read_nullable_utf()
        extra_fields['isrc'] = reader.read_nullable_utf()

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
            'isSeekable': not is_stream,
            'sourceName': source,
            **extra_fields
        }
    }

    return AudioTrack(track_object, 0, position=position, encoder_version=version)


def encode_track(track: Dict[str, Union[Optional[str], int, bool]]) -> Tuple[int, str]:
    """
    Encodes a track dict into a base64 string, readable by the Lavalink server.

    A track should have *at least* the following keys:
    ``title``, ``author``, ``length``, ``identifier``, ``isStream``, ``uri``, ``sourceName`` and ``position``.

    If the track is a v3 track, it should have the following additional fields:
    ``artworkUrl`` and ``isrc``. isrc can be ``None`` if not applicable.

    Parameters
    ----------
    track: Dict[str, Union[Optional[str], int, bool]]
        The track dict to serialize.

    Raises
    ------
    :class:`InvalidTrack`
        If the track has unexpected, or missing keys, possibly due to an incompatible version or another reason.

    Returns
    -------
    Tuple[int, str]
        A tuple containing (track_version, encoded_track).
        For example, if a track was encoded as version 3, the return value will be ``(3, '...really long track string...')``.
    """
    track_keys = track.keys()  # set(track) is faster for larger collections, but slower for smaller.

    if not V2_KEYSET <= track_keys:  # V2_KEYSET contains the minimum number of fields required to successfully encode a track.
        missing_keys = [k for k in V2_KEYSET if k not in track]

        raise InvalidTrack(f'Track object is missing keys required for serialization: {", ".join(missing_keys)}')

    if V3_KEYSET <= track_keys:
        return (3, encode_track_v3(track))

    return (2, encode_track_v2(track))


def encode_track_v2(track: Dict[str, Union[Optional[str], bool, int]]) -> str:
    assert V2_KEYSET <= track.keys()

    writer = DataWriter()

    version = struct.pack('B', 2)
    writer.write_byte(version)
    _write_track_common(track, writer)
    writer.write_utf(track['sourceName'])
    writer.write_long(track['position'])

    enc = writer.finish()
    return b64encode(enc).decode()


def encode_track_v3(track: Dict[str, Union[Optional[str], bool, int]]) -> str:
    assert V3_KEYSET <= track.keys()

    writer = DataWriter()
    version = struct.pack('B', 3)
    writer.write_byte(version)
    _write_track_common(track, writer)
    writer.write_nullable_utf(track['artworkUrl'])
    writer.write_nullable_utf(track['isrc'])
    writer.write_utf(track['sourceName'])
    writer.write_long(track['position'])

    enc = writer.finish()
    return b64encode(enc).decode()
