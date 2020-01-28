import struct
from base64 import b64decode
from io import BytesIO


class DataReader:
    def __init__(self, ts):
        self._buf = BytesIO(b64decode(ts))

    def _read(self, n):
        return self._buf.read(n)

    def read_byte(self):
        return self._read(1)

    def read_boolean(self):
        return self.read_byte() != 0

    def read_unsigned_short(self):  # 2 bytes
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
