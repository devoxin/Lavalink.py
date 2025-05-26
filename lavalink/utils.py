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
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from .common import MISSING
from .dataio import DataReader, DataWriter
from .errors import InvalidTrack
from .player import AudioTrack
from .source_decoders import DEFAULT_DECODER_MAPPING

__all__ = (
    "V2_KEYSET",
    "V3_KEYSET",
    "timestamp_to_millis",
    "format_time",
    "parse_time",
    "decode_track",
    "encode_track",
    "encode_track_v2",
    "encode_track_v3",
)

V2_KEYSET = {'title', 'author', 'length', 'identifier', 'isStream', 'uri', 'sourceName', 'position'}
V3_KEYSET = V2_KEYSET | {'artworkUrl', 'isrc'}


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
    except ValueError as error:
        raise ValueError('Timestamp should consist of integers and colons only') from error

    if not sections:
        raise TypeError('An invalid timestamp was provided, a timestamp should look like 1:30')

    if len(sections) > 4:
        raise TypeError('Too many segments within the provided timestamp! Provide no more than 4 segments.')

    if len(sections) == 4:
        days, hours, minutes, seconds = map(int, sections)
        return (days * 86400000) + (hours * 3600000) + (minutes * 60000) + (seconds * 1000)

    if len(sections) == 3:
        hours, minutes, seconds = map(int, sections)
        return (hours * 3600000) + (minutes * 60000) + (seconds * 1000)

    if len(sections) == 2:
        minutes, seconds = map(int, sections)
        return (minutes * 60000) + (seconds * 1000)

    seconds, = map(int, sections)
    return seconds * 1000


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

    return f'{hours:02.0f}:{minutes:02.0f}:{seconds:02.0f}'


def parse_time(time: int) -> Tuple[float, float, float, float]:
    """
    Parses the given time into days, hours, minutes and seconds.
    Useful for formatting time yourself.

    Parameters
    ----------
    time: :class:`int`
        The time in milliseconds.

    Returns
    -------
    Tuple[:class:`float`, :class:`float`, :class:`float`, :class:`float`]
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


def _write_track_common(track: Dict[str, Any], writer: DataWriter):
    writer.write_utf(track['title'])
    writer.write_utf(track['author'])
    writer.write_long(track['length'])
    writer.write_utf(track['identifier'])
    writer.write_boolean(track['isStream'])
    writer.write_nullable_utf(track['uri'])


def decode_track(track: str,  # pylint: disable=R0914
                 source_decoders: Mapping[str, Callable[[DataReader], Mapping[str, Any]]] = MISSING) -> AudioTrack:
    """
    Decodes a base64 track string into an AudioTrack object.

    Parameters
    ----------
    track: :class:`str`
        The base64 track string.
    source_decoders: Mapping[:class:`str`, Callable[[:class:`DataReader`], Dict[:class:`str`, Any]]]
        A mapping of source-specific decoders to use.
        Some Lavaplayer sources have additional fields encoded on a per-source manager basis, so you can
        specify a mapping of decoders that will handle decoding these additional fields. You can find some
        example decoders within the ``source_decoders`` file. This isn't required for all sources, so ensure
        that you need them before specifying.

        To overwrite library-provided decoders, just specify them within the mapping and the new decoders will
        be used.

    Returns
    -------
    :class:`AudioTrack`
    """
    decoders = DEFAULT_DECODER_MAPPING.copy()

    if source_decoders is not MISSING:
        decoders.update(source_decoders)

    reader = DataReader(track)

    flags = (reader.read_int() & 0xC0000000) >> 30
    version, = struct.unpack('B', reader.read_byte()) if flags & 1 != 0 else (1,)

    title, author, length, identifier, is_stream, uri = _read_track_common(reader)
    extra_fields = {}

    if version == 3:
        extra_fields['artworkUrl'] = reader.read_nullable_utf()
        extra_fields['isrc'] = reader.read_nullable_utf()

    source = reader.read_utf().decode()
    source_specific_fields = {}

    if source in decoders:
        source_specific_fields.update(decoders[source](reader))

    position = reader.read_long()

    track_object = {
        'encoded': track,
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

    return AudioTrack(track_object, 0, position=position, encoder_version=version,
                      source_specific=source_specific_fields)


def encode_track(track: Dict[str, Any],
                 source_encoders: Mapping[str, Callable[[DataWriter, Dict[str, Any]], None]] = MISSING) -> Tuple[int, str]:
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
    source_encoders: Mapping[:class:`str`, Callable[[:class:`DataWriter`]]
        A mapping of source-specific encoders to use.
        Some Lavaplayer sources have additional fields encoded on a per-source manager basis, so you can
        specify a mapping of encoders that will handle encoding these additional fields. This isn't required
        for all sources, so ensure that you need them before specifying.

        The mapping must be in the format of something like ``{'http': http_encoder_function}``, where the
        key ``str`` is the name of the source. These functions will only be called if track's ``sourceName``
        field matches.

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
        return (3, encode_track_v3(track, source_encoders))

    return (2, encode_track_v2(track, source_encoders))


def encode_track_v2(track: Dict[str, Any],
                    source_encoders: Mapping[str, Callable[[DataWriter, Dict[str, Any]], None]] = MISSING) -> str:
    assert V2_KEYSET <= track.keys()

    writer = DataWriter()

    version = struct.pack('B', 2)
    writer.write_byte(version)
    _write_track_common(track, writer)
    writer.write_utf(track['sourceName'])

    if source_encoders is not MISSING and track['sourceName'] in source_encoders:
        source_encoders[track['sourceName']](writer, track)

    writer.write_long(track['position'])

    enc = writer.finish()
    return b64encode(enc).decode()


def encode_track_v3(track: Dict[str, Any],
                    source_encoders: Mapping[str, Callable[[DataWriter, Dict[str, Any]], None]] = MISSING) -> str:
    assert V3_KEYSET <= track.keys()

    writer = DataWriter()
    version = struct.pack('B', 3)
    writer.write_byte(version)
    _write_track_common(track, writer)
    writer.write_nullable_utf(track['artworkUrl'])
    writer.write_nullable_utf(track['isrc'])
    writer.write_utf(track['sourceName'])

    if source_encoders is not MISSING and track['sourceName'] in source_encoders:
        source_encoders[track['sourceName']](writer, track)

    writer.write_long(track['position'])

    enc = writer.finish()
    return b64encode(enc).decode()
