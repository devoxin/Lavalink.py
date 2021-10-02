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

from .utfm_codec import read_utfm


class DataReader:
    def __init__(self, ts):
        self._buf = BytesIO(b64decode(ts))

    def _read(self, count):
        return self._buf.read(count)

    def read_byte(self):
        return self._read(1)

    def read_boolean(self):
        result, = struct.unpack('B', self.read_byte())
        return result != 0

    def read_unsigned_short(self):
        result, = struct.unpack('>H', self._read(2))
        return result

    def read_int(self):
        result, = struct.unpack('>i', self._read(4))
        return result

    def read_long(self):
        result, = struct.unpack('>Q', self._read(8))
        return result

    def read_utf(self):
        text_length = self.read_unsigned_short()
        return self._read(text_length)

    def read_utfm(self):
        text_length = self.read_unsigned_short()
        utf_string = self._read(text_length)
        return read_utfm(text_length, utf_string)


class DataWriter:
    def __init__(self):
        self._buf = BytesIO()

    def _write(self, data):
        self._buf.write(data)

    def write_byte(self, byte):
        self._buf.write(byte)

    def write_boolean(self, boolean):
        enc = struct.pack('B', 1 if boolean else 0)
        self.write_byte(enc)

    def write_unsigned_short(self, short):
        enc = struct.pack('>H', short)
        self._write(enc)

    def write_int(self, integer):
        enc = struct.pack('>i', integer)
        self._write(enc)

    def write_long(self, long_value):
        enc = struct.pack('>Q', long_value)
        self._write(enc)

    def write_utf(self, utf_string):
        utf = utf_string.encode('utf8')
        byte_len = len(utf)

        if byte_len > 65535:
            raise OverflowError('UTF string may not exceed 65535 bytes!')

        self.write_unsigned_short(byte_len)
        self._write(utf)

    def finish(self):
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
