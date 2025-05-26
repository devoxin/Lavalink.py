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
from typing import Any, Callable, Dict, Mapping

from .dataio import DataReader

__all__ = (
    "decode_probe_info",
    "decode_lavasrc_fields",
    "DEFAULT_DECODER_MAPPING",
)


def decode_probe_info(reader: DataReader) -> Mapping[str, Any]:
    probe_info = reader.read_utf().decode()
    return {'probe_info': probe_info}


def decode_lavasrc_fields(reader: DataReader) -> Mapping[str, Any]:
    if reader.remaining <= 8:  # 8 bytes (long) = position field
        return {}

    album_name = reader.read_nullable_utf()
    album_url = reader.read_nullable_utf()
    artist_url = reader.read_nullable_utf()
    artist_artwork_url = reader.read_nullable_utf()
    preview_url = reader.read_nullable_utf()
    is_preview = reader.read_boolean()

    return {
        'album_name': album_name,
        'album_url': album_url,
        'artist_url': artist_url,
        'artist_artwork_url': artist_artwork_url,
        'preview_url': preview_url,
        'is_preview': is_preview
    }


DEFAULT_DECODER_MAPPING: Dict[str, Callable[[DataReader], Mapping[str, Any]]] = {
    'http': decode_probe_info,
    'local': decode_probe_info,
    'deezer': decode_lavasrc_fields,
    'spotify': decode_lavasrc_fields,
    'applemusic': decode_lavasrc_fields
}
