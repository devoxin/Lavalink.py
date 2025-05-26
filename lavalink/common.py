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
from typing import Any, Literal, Optional, TypedDict

__all__ = (
    "MISSING",
    "VoiceStateUpdateData",
    "VoiceServerUpdateData",
    "VoiceStateUpdatePayload",
    "VoiceServerUpdatePayload",
)


class _MissingObj:
    __slots__ = ()

    def __repr__(self):
        return '...'


MISSING: Any = _MissingObj()


class VoiceStateUpdateData(TypedDict):
    guild_id: str
    channel_id: Optional[str]
    user_id: str
    session_id: str


class VoiceServerUpdateData(TypedDict):
    guild_id: str
    endpoint: Optional[str]
    token: str


class VoiceStateUpdatePayload(TypedDict):
    t: Literal['VOICE_STATE_UPDATE']
    d: VoiceStateUpdateData


class VoiceServerUpdatePayload(TypedDict):
    t: Literal['VOICE_SERVER_UPDATE']
    d: VoiceServerUpdateData
