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

This module serves to contain all entities which are deserialized using responses from
the Lavalink server.
"""
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Union

from .errors import InvalidTrack

if TYPE_CHECKING:
    from .abc import DeferredAudioTrack


class AudioTrack:
    """
    .. _ISRC: https://en.wikipedia.org/wiki/International_Standard_Recording_Code

    Represents an AudioTrack.

    Parameters
    ----------
    data: Union[:class:`dict`, :class:`AudioTrack`]
        The data to initialise an AudioTrack from.
    requester: :class:`any`
        The requester of the track.
    extra: :class:`dict`
        Any extra information to store in this AudioTrack.

    Attributes
    ----------
    track: Optional[:class:`str`]
        The base64-encoded string representing a Lavalink-readable AudioTrack.
        This is marked optional as it could be None when it's not set by a custom :class:`Source`,
        which is expected behaviour when the subclass is a :class:`DeferredAudioTrack`.
    identifier: :class:`str`
        The track's id. For example, a youtube track's identifier will look like ``dQw4w9WgXcQ``.
    is_seekable: :class:`bool`
        Whether the track supports seeking.
    author: :class:`str`
        The track's uploader.
    duration: :class:`int`
        The duration of the track, in milliseconds.
    stream: :class:`bool`
        Whether the track is a live-stream.
    title: :class:`str`
        The title of the track.
    uri: :class:`str`
        The full URL of track.
    artwork_url: Optional[:class:`str`]
        A URL pointing to the track's artwork, if applicable.
    isrc: Optional[:class:`str`]
        The `ISRC`_ for the track, if applicable.
    position: :class:`int`
        The playback position of the track, in milliseconds.
        This is a read-only property; setting it won't have any effect.
    source_name: :class:`str`
        The name of the source that this track was created by.
    requester: :class:`int`
        The ID of the user that requested this track.
    extra: :class:`dict`
        Any extra properties given to this AudioTrack will be stored here.
    """
    __slots__ = ('_raw', 'track', 'identifier', 'is_seekable', 'author', 'duration', 'stream', 'title', 'uri',
                 'artwork_url', 'isrc', 'position', 'source_name', 'extra')

    def __init__(self, data: dict, requester: int = 0, **extra):
        try:
            if isinstance(data, AudioTrack):
                extra = {**data.extra, **extra}
                data = data._raw

            self._raw = data

            info = data.get('info', data)
            self.track: Optional[str] = data.get('track')
            self.identifier: str = info['identifier']
            self.is_seekable: bool = info['isSeekable']
            self.author: str = info['author']
            self.duration: int = info['length']
            self.stream: bool = info['isStream']
            self.title: str = info['title']
            self.uri: str = info['uri']
            self.artwork_url: Optional[str] = info.get('artworkUrl')
            self.isrc: Optional[str] = info.get('isrc')
            self.position: int = info.get('position', 0)
            self.source_name: str = info.get('sourceName', 'unknown')
            self.extra: dict = {**extra, 'requester': requester}
        except KeyError as ke:
            missing_key, = ke.args
            raise InvalidTrack('Cannot build a track from partial data! (Missing key: {})'.format(missing_key)) from None

    def __getitem__(self, name):
        if name == 'info':
            return self

        return super().__getattribute__(name)

    @classmethod
    def from_dict(cls, mapping: dict):
        return cls(mapping)

    @property
    def requester(self) -> int:
        return self.extra['requester']

    @requester.setter
    def requester(self, requester) -> int:
        self.extra['requester'] = requester

    def __repr__(self):
        return '<AudioTrack title={0.title} identifier={0.identifier}>'.format(self)


class LoadType(Enum):
    TRACK = 'TRACK_LOADED'
    PLAYLIST = 'PLAYLIST_LOADED'
    SEARCH = 'SEARCH_RESULT'
    NO_MATCHES = 'NO_MATCHES'
    LOAD_FAILED = 'LOAD_FAILED'

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value  # pylint: disable=comparison-with-callable

        if isinstance(other, str):
            return self.value == other  # pylint: disable=comparison-with-callable

        raise NotImplementedError

    @classmethod
    def from_str(cls, other: str):
        try:
            return cls[other.upper()]
        except KeyError:
            try:
                return cls(other.upper())
            except ValueError as ve:
                raise ValueError('{} is not a valid LoadType enum!'.format(other)) from ve


class PlaylistInfo:
    """
    Attributes
    ----------
    name: :class:`str`
        The name of the playlist.
    selected_track: :class:`int`
        The index of the selected/highlighted track.
        This will be -1 if there is no selected track.
    """
    def __init__(self, name: str, selected_track: int = -1):
        self.name: str = name
        self.selected_track: int = selected_track

    def __getitem__(self, k):  # Exists only for compatibility, don't blame me
        if k == 'selectedTrack':
            k = 'selected_track'
        return self.__getattribute__(k)

    @classmethod
    def from_dict(cls, mapping: dict):
        return cls(mapping.get('name'), mapping.get('selectedTrack', -1))

    @classmethod
    def none(cls):
        return cls('', -1)

    def __repr__(self):
        return '<PlaylistInfo name={0.name} selected_track={0.selected_track}>'.format(self)


class LoadResult:
    """
    Attributes
    ----------
    load_type: :class:`LoadType`
        The load type of this result.
    tracks: List[Union[:class:`AudioTrack`, :class:`DeferredAudioTrack`]]
        The tracks in this result.
    playlist_info: Optional[:class:`PlaylistInfo`]
        The playlist metadata for this result.
        The :class:`PlaylistInfo` could contain empty/false data if the :class:`LoadType`
        is not :enum:`LoadType.PLAYLIST`.
    """
    def __init__(self, load_type: LoadType, tracks: List[Union[AudioTrack, 'DeferredAudioTrack']],
                 playlist_info: Optional[PlaylistInfo] = PlaylistInfo.none()):
        self.load_type: LoadType = load_type
        self.playlist_info: PlaylistInfo = playlist_info
        self.tracks: List[Union[AudioTrack, 'DeferredAudioTrack']] = tracks

    def __getitem__(self, k):  # Exists only for compatibility, don't blame me
        if k == 'loadType':
            k = 'load_type'
        elif k == 'playlistInfo':
            k = 'playlist_info'

        return self.__getattribute__(k)

    @classmethod
    def from_dict(cls, mapping: dict):
        load_type = LoadType.from_str(mapping.get('loadType'))
        playlist_info = PlaylistInfo.from_dict(mapping.get('playlistInfo')) if mapping.get('playlistInfo') is not None else None
        tracks = [AudioTrack(track, 0) for track in mapping.get('tracks')]
        return cls(load_type, tracks, playlist_info)

    @property
    def selected_track(self) -> Optional[AudioTrack]:
        """
        Convenience method for returning the selected track using
        :attr:`PlaylistInfo.selected_track`.

        This could be ``None`` if :attr:`playlist_info` is ``None``,
        or :attr:`PlaylistInfo.selected_track` is an invalid number.

        Returns
        -------
        Optional[:class:`AudioTrack`]
        """
        if self.playlist_info is not None:
            index = self.playlist_info.selected_track

            if 0 <= index < len(self.tracks):
                return self.tracks[index]

        return None

    def __repr__(self):
        return '<LoadResult load_type={0.load_type} playlist_info={0.playlist_info} tracks=[{1} item(s)]>'.format(self, len(self.tracks))


class Plugin:
    """
    Represents a Lavalink server plugin.

    Parameters
    ----------
    data: :class:`dict`
        The data to initialise a Plugin from.

    Attributes
    ----------
    name: :class:`str`
        The name of the plugin.
    version: :class:`str`
        The version of the plugin.
    """
    __slots__ = ('name', 'version')

    def __init__(self, data: dict):
        self.name: str = data['name']
        self.version: str = data['version']

    def __str__(self):
        return '{0.name} v{0.version}'.format(self)

    def __repr__(self):
        return '<Plugin name={0.name} version={0.version}>'.format(self)
