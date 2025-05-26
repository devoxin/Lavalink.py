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

__all__ = (
    "read_utfm",
)


def read_utfm(utf_len: int, utf_bytes: bytes) -> str:
    chars = []
    count = 0

    while count < utf_len:
        char = utf_bytes[count] & 0xff
        if char > 127:
            break

        count += 1
        chars.append(chr(char))

    while count < utf_len:
        char = utf_bytes[count] & 0xff
        shift = char >> 4

        if 0 <= shift <= 7:
            count += 1
            chars.append(chr(char))
        elif 12 <= shift <= 13:
            count += 2
            if count > utf_len:
                raise UnicodeDecodeError('utf8', b'', 0, utf_len, 'malformed input: partial character at end')
            char2 = utf_bytes[count - 1]
            if (char2 & 0xC0) != 0x80:
                raise UnicodeDecodeError('utf8', b'', 0, utf_len, f'malformed input around byte {count}')

            char_shift = ((char & 0x1F) << 6) | (char2 & 0x3F)
            chars.append(chr(char_shift))
        elif shift == 14:
            count += 3
            if count > utf_len:
                raise UnicodeDecodeError('utf8', b'', 0, utf_len, 'malformed input: partial character at end')

            char2 = utf_bytes[count - 2]
            char3 = utf_bytes[count - 1]

            if (char2 & 0xC0) != 0x80 or (char3 & 0xC0) != 0x80:
                raise UnicodeDecodeError('utf8', b'', 0, utf_len, f'malformed input around byte {(count - 1)}')

            char_shift = ((char & 0x0F) << 12) | ((char2 & 0x3F) << 6) | ((char3 & 0x3F) << 0)
            chars.append(chr(char_shift))
        else:
            raise UnicodeDecodeError('utf8', b'', 0, utf_len, f'malformed input around byte {count}')

    return ''.join(chars).encode('utf-16', 'surrogatepass').decode('utf-16')
