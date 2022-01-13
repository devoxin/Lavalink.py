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
from typing import Union


class Filter:
    def __init__(self, values: Union[dict, list]):
        self.values = values

    def update(self, **kwargs):
        """ docs todo """
        raise NotImplementedError

    def serialize(self) -> dict:
        """ docs todo """
        raise NotImplementedError


class Equalizer(Filter):
    def __init__(self):
        super().__init__([0.0] * 15)

    def update(self, **kwargs):
        """
        Modifies the gain of each specified band.
        There are 15 total bands (indexes 0 to 14) that can be modified.
        The meaningful range of each band is -0.25 (muted) to 1.0. A gain of 0.25 doubles the frequency.
        The default gain is 0.0.
        Modifying the gain could alter the volume of output.

        The frequencies of each band are as follows:
        25 Hz, 40 Hz, 63 Hz, 100 Hz, 160 Hz, 250 Hz, 400 Hz, 630 Hz, 1k Hz, 1.6k Hz, 2.5k Hz, 4k Hz, 6.3k Hz, 10k Hz, 16k Hz
        Leftmost frequency represents band 0, rightmost frequency represents band 14.

        Note
        ----
        You can provide either ``bands`` OR ``band`` and ``gain`` for the parameters.

        Parameters
        ----------
        bands: list[tuple[:class:`int`, :class:`float`]]
            The bands to modify, and their respective gains.
        band: :class:`int`
            The band to modify.
        gain: :class:`float`
            The new gain of the band.
        """
        if 'bands' in kwargs:
            bands = kwargs.pop('bands')

            sanity_check = isinstance(bands, list) and all(isinstance(pair, tuple) for pair in bands) and \
                all(isinstance(band, int) and isinstance(gain, float) for band, gain in bands) and \
                all(0 <= band <= 14 and -0.25 <= gain <= 1.0 for band, gain in bands)

            if not sanity_check:
                raise ValueError('Bands must be a list of tuple representing (band: int, gain: float) with values between '
                                 '0 to 14, and -0.25 to 1.0 respectively')

            for band, gain in bands:
                self.values[band] = gain
        elif 'band' in kwargs and 'gain' in kwargs:
            band = int(kwargs.pop('band'))
            gain = float(kwargs.pop('gain'))
            # don't bother propagating the potential ValueErrors raised by these 2 statements
            # The users can handle those.

            if not 0 <= band <= 14:
                raise ValueError('Band must be between 0 and 14 (start and end inclusive)')

            if not -0.25 <= gain <= 1.0:
                raise ValueError('Gain must be between -0.25 and 1.0 (start and end inclusive)')

            self.values[band] = gain
        else:
            raise KeyError('Expected parameter bands OR band and gain, but neither were provided')

    def serialize(self) -> dict:
        return {'equalizer': [{'band': band, 'gain': gain} for band, gain in enumerate(self.values)]}


class Karaoke(Filter):
    def __init__(self):
        super().__init__({'level': 1.0, 'monoLevel': 1.0, 'filterBand': 220.0, 'filterWidth': 100.0})

    def update(self, **kwargs):
        """
        Parameters
        ----------
        level: :class:`float`
            The level of the Karaoke effect.
        monoLevel: :class:`float`
            The mono level of the Karaoke effect.
        filterBand: :class:`float`
            The frequency of the band to filter.
        filterWidth: :class:`float`
            The width of the filter.
        """
        if 'level' in kwargs:
            self.values['level'] = float(kwargs.pop('level'))

        if 'monoLevel' in kwargs:
            self.values['monoLevel'] = float(kwargs.pop('monoLevel'))

        if 'filterBand' in kwargs:
            self.values['filterBand'] = float(kwargs.pop('filterBand'))

        if 'filterWidth' in kwargs:
            self.values['filterWidth'] = float(kwargs.pop('filterWidth'))

    def serialize(self) -> dict:
        return {'karaoke': self.values}


class Timescale(Filter):
    def __init__(self):
        super().__init__({'speed': 1.0, 'pitch': 1.0, 'rate': 1.0})

    def update(self, **kwargs):
        """
        Parameters
        ----------
        speed: :class:`float`
            The playback speed.
        pitch: :class:`float`
            The pitch of the audio.
        rate: :class:`float`
            The playback rate.
        """
        if 'speed' in kwargs:
            self.values['speed'] = float(kwargs.pop('speed'))

        if 'pitch' in kwargs:
            self.values['pitch'] = float(kwargs.pop('pitch'))

        if 'rate' in kwargs:
            self.values['rate'] = float(kwargs.pop('rate'))

    def serialize(self) -> dict:
        return {'timescale': self.values}


class Tremolo(Filter):
    def __init__(self):
        super().__init__({'frequency': 2.0, 'depth': 0.5})

    def update(self, **kwargs):
        """
        Parameters
        ----------
        frequency: :class:`float`
            How frequently the effect should occur.
        depth: :class:`float`
            The "strength" of the effect.
        """
        if 'frequency' in kwargs:
            frequency = float(kwargs.pop('frequency'))

            if frequency < 0:
                raise ValueError('Frequency must be bigger than 0')

            self.values['frequency'] = frequency

        if 'depth' in kwargs:
            depth = float(kwargs.pop('depth'))

            if not 0 < depth <= 1:
                raise ValueError('Depth must be bigger than 0, and less than or equal to 1.')

            self.values['depth'] = depth

    def serialize(self) -> dict:
        return {'tremolo': self.values}


class Vibrato(Filter):
    def __init__(self):
        super().__init__({'frequency': 2.0, 'depth': 0.5})

    def update(self, **kwargs):
        """
        Parameters
        ----------
        frequency: :class:`float`
            How frequently the effect should occur.
        depth: :class:`float`
            The "strength" of the effect.
        """
        if 'frequency' in kwargs:
            frequency = float(kwargs.pop('frequency'))

            if not 0 < frequency <= 14:
                raise ValueError('Frequency must be bigger than 0, and less than or equal to 14')

            self.values['frequency'] = frequency

        if 'depth' in kwargs:
            depth = float(kwargs.pop('depth'))

            if not 0 < depth <= 1:
                raise ValueError('Depth must be bigger than 0, and less than or equal to 1.')

            self.values['depth'] = depth

    def serialize(self) -> dict:
        return {'vibrato': self.values}
