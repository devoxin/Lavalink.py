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
from typing import Final


class ExponentialBackoff:
    """
    Basic exponential backoff calculator.
    """
    __slots__ = ('base', 'max', '_current')

    def __init__(self, base: float = 1.0, max: float = 30.0) -> None:  # pylint: disable=redefined-builtin
        self.base: Final[float] = min(base, max)
        self.max: Final[float] = max
        self._current: float = self.base

    @property
    def current(self) -> float:
        return self._current

    def next(self) -> float:
        current = self._current
        self._current = min(current * 2, self.max)
        return current

    def reset(self) -> None:
        self._current = self.base
