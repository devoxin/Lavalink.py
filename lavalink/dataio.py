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
from base64 import b64decode
from io import BytesIO
from typing import Final, Optional

from .utfm_codec import read_utfm


class DataReader:
    __slots__ = ('_buf',)

    def __init__(self, base64_str: str):
        self._buf: Final[BytesIO] = BytesIO(b64decode(base64_str))

    @property
    def remaining(self) -> int:
        """ The amount of bytes left to be read. """
        return self._buf.getbuffer().nbytes - self._buf.tell()

    def _read(self, count: int):
        return self._buf.read(count)

    def read_byte(self) -> bytes:
        """
        Reads a single byte from the stream.

        Returns
        -------
        :class:`bytes`
        """
        return self._read(1)

    def read_boolean(self) -> bool:
        """
        Reads a bool from the stream.

        Returns
        -------
        :class:`bool`
        """
        result, = struct.unpack('B', self.read_byte())
        return result != 0

    def read_unsigned_short(self) -> int:
        """
        Reads an unsigned short from the stream.

        Returns
        -------
        :class:`int`
        """
        result, = struct.unpack('>H', self._read(2))
        return result

    def read_int(self) -> int:
        """
        Reads an int from the stream.

        Returns
        -------
        :class:`int`
        """
        result, = struct.unpack('>i', self._read(4))
        return result

    def read_long(self) -> int:
        """
        Reads a long from the stream.

        Returns
        -------
        :class:`int`
        """
        result, = struct.unpack('>Q', self._read(8))
        return result

    def read_nullable_utf(self, utfm: bool = False) -> Optional[str]:
        """
        .. _modified UTF: https://en.wikipedia.org/wiki/UTF-8#Modified_UTF-8

        Reads an optional UTF string from the stream.

        Internally, this just reads a bool and then a string if the bool is ``True``.

        Parameters
        ----------
        utfm: :class:`bool`
            Whether to read the string as `modified UTF`_.

        Returns
        -------
        Optional[:class:`str`]
        """
        exists = self.read_boolean()

        if not exists:
            return None

        return self.read_utfm() if utfm else self.read_utf().decode()

    def read_utf(self) -> bytes:
        """
        Reads a UTF string from the stream.

        Returns
        -------
        :class:`bytes`
        """
        text_length = self.read_unsigned_short()
        return self._read(text_length)

    def read_utfm(self) -> str:
        """
        .. _modified UTF: https://en.wikipedia.org/wiki/UTF-8#Modified_UTF-8

        Reads a UTF string from the stream.

        This method is different to :func:`read_utf` as it accounts for
        different encoding methods utilised by Java's streams, which uses `modified UTF`_
        for character encoding.

        Returns
        -------
        :class:`str`
        """
        text_length = self.read_unsigned_short()
        utf_string = self._read(text_length)
        return read_utfm(text_length, utf_string)


class DataWriter:
    __slots__ = ('_buf',)

    def __init__(self):
        self._buf: Final[BytesIO] = BytesIO()

    def _write(self, data):
        self._buf.write(data)

    def write_byte(self, byte):
        """
        Writes a single byte to the stream.

        Parameters
        ----------
        byte: Any
            This can be anything ``BytesIO.write()`` accepts.
        """
        self._buf.write(byte)

    def write_boolean(self, boolean: bool):
        """
        Writes a bool to the stream.

        Parameters
        ----------
        boolean: :class:`bool`
            The bool to write.
        """
        enc = struct.pack('B', 1 if boolean else 0)
        self.write_byte(enc)

    def write_unsigned_short(self, short: int):
        """
        Writes an unsigned short to the stream.

        Parameters
        ----------
        short: :class:`int`
            The unsigned short to write.
        """
        enc = struct.pack('>H', short)
        self._write(enc)

    def write_int(self, integer: int):
        """
        Writes an int to the stream.

        Parameters
        ----------
        integer: :class:`int`
            The integer to write.
        """
        enc = struct.pack('>i', integer)
        self._write(enc)

    def write_long(self, long_value: int):
        """
        Writes a long to the stream.

        Parameters
        ----------
        long_value: :class:`int`
            The long to write.
        """
        enc = struct.pack('>Q', long_value)
        self._write(enc)

    def write_nullable_utf(self, utf_string: Optional[str]):
        """
        Writes an optional string to the stream.

        Parameters
        ----------
        utf_string: Optional[:class:`str`]
            The optional string to write.
        """
        self.write_boolean(bool(utf_string))

        if utf_string:
            self.write_utf(utf_string)

    def write_utf(self, utf_string: str):
        """
        Writes a utf string to the stream.

        Parameters
        ----------
        utf_string: :class:`str`
            The string to write.
        """
        utf = utf_string.encode('utf8')
        byte_len = len(utf)

        if byte_len > 65535:
            raise OverflowError('UTF string may not exceed 65535 bytes!')

        self.write_unsigned_short(byte_len)
        self._write(utf)

    def finish(self) -> bytes:
        """
        Finalizes the stream by writing the necessary flags, byte length etc.

        Returns
        ----------
        :class:`bytes`
            The finalized stream.
        """
        with BytesIO() as track_buf:
            byte_len = self._buf.getbuffer().nbytes
            flags = byte_len | (1 << 30)
            enc_flags = struct.pack('>i', flags)
            track_buf.write(enc_flags)

            self._buf.seek(0)
            track_buf.write(self._buf.read())
            self._buf.close()

            track_buf.seek(0)
            return track_buf.read()
