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
    def __init__(self, values: Union[dict, list, float]):
        self.values = values

    def update(self, **kwargs):
        """ Updates the internal values to match those provided. """
        raise NotImplementedError

    def serialize(self) -> dict:
        """ Transforms the internal values into a dict matching the structure Lavalink expects. """
        raise NotImplementedError


class Volume(Filter):
    """
    Adjusts the audio output volume.
    """
    def __init__(self):
        super().__init__(1.0)

    def update(self, **kwargs):
        """
        Modifies the player volume.
        This uses LavaDSP's volume filter, rather than Lavaplayer's native
        volume changer.

        Note
        ----
        The limits are:

            0 ≤ volume ≤ 5

        Parameters
        ----------
        volume: :class:`float`
            The new volume of the player. 1.0 means 100%/default.
        """
        if 'volume' in kwargs:
            volume = float(kwargs.pop('volume'))

            if not 0 <= volume <= 5:
                raise ValueError('volume must be bigger than or equal to 0, and less than or equal to 5.')

            self.values = volume

    def serialize(self) -> dict:
        return {'volume': self.values}


class Equalizer(Filter):
    """
    Allows modifying the gain of 15 bands, to boost or reduce the volume of specific frequency ranges.
    For example, this could be used to boost the low (bass) frequencies to act as a 'bass boost'.
    """
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

        The limits are:

            0 ≤ band ≤ 14

            -0.25 ≤ gain ≤ 1.0

        Parameters
        ----------
        bands: List[Tuple[:class:`int`, :class:`float`]]
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
    """
    Allows for isolating a frequency range (commonly, the vocal range).
    Useful for 'karaoke'/sing-along.
    """
    def __init__(self):
        super().__init__({'level': 1.0, 'monoLevel': 1.0, 'filterBand': 220.0, 'filterWidth': 100.0})

    def update(self, **kwargs):
        """
        Parameters
        ----------
        level: :class:`float`
            The level of the Karaoke effect.
        mono_level: :class:`float`
            The mono level of the Karaoke effect.
        filter_band: :class:`float`
            The frequency of the band to filter.
        filter_width: :class:`float`
            The width of the filter.
        """
        if 'level' in kwargs:
            self.values['level'] = float(kwargs.pop('level'))

        if 'mono_level' in kwargs:
            self.values['monoLevel'] = float(kwargs.pop('mono_level'))

        if 'filter_band' in kwargs:
            self.values['filterBand'] = float(kwargs.pop('filter_band'))

        if 'filter_width' in kwargs:
            self.values['filterWidth'] = float(kwargs.pop('filter_width'))

    def serialize(self) -> dict:
        return {'karaoke': self.values}


class Timescale(Filter):
    """
    Allows speeding up/slowing down the audio, adjusting the pitch and playback rate.
    """
    def __init__(self):
        super().__init__({'speed': 1.0, 'pitch': 1.0, 'rate': 1.0})

    def update(self, **kwargs):
        """
        Note
        ----
        The limits are:

            0.1 ≤ speed

            0.1 ≤ pitch

            0.1 ≤ rate

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
            speed = float(kwargs.pop('speed'))

            if speed <= 0:
                raise ValueError('Speed must be bigger than 0')

            self.values['speed'] = speed

        if 'pitch' in kwargs:
            pitch = float(kwargs.pop('pitch'))

            if pitch <= 0:
                raise ValueError('Pitch must be bigger than 0')

            self.values['pitch'] = pitch

        if 'rate' in kwargs:
            rate = float(kwargs.pop('rate'))

            if rate <= 0:
                raise ValueError('Rate must be bigger than 0')

            self.values['rate'] = rate

    def serialize(self) -> dict:
        return {'timescale': self.values}


class Tremolo(Filter):
    """
    Applies a 'tremble' effect to the audio.
    """
    def __init__(self):
        super().__init__({'frequency': 2.0, 'depth': 0.5})

    def update(self, **kwargs):
        """
        Note
        ----
        The limits are:

            0 < frequency

            0 < depth ≤ 1

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
    """
    Applies a 'wobble' effect to the audio.
    """
    def __init__(self):
        super().__init__({'frequency': 2.0, 'depth': 0.5})

    def update(self, **kwargs):
        """
        Note
        ----
        The limits are:

            0 < frequency ≤ 14

            0 < depth ≤ 1

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


class Rotation(Filter):
    """
    Phases the audio in and out of the left and right channels in an alternating manner.
    This is commonly used to create the 8D effect.
    """
    def __init__(self):
        super().__init__({'rotationHz': 0.0})

    def update(self, **kwargs):
        """
        Note
        ----
        The limits are:

            0 ≤ rotation_hz

        Parameters
        ----------
        rotation_hz: :class:`float`
            How frequently the effect should occur.
        """
        if 'rotation_hz' in kwargs:
            rotation_hz = float(kwargs.pop('rotation_hz'))

            if rotation_hz < 0:
                raise ValueError('rotationHz must be bigger than or equal to 0')

            self.values['rotationHz'] = rotation_hz

    def serialize(self) -> dict:
        return {'rotation': self.values}


class LowPass(Filter):
    """
    Applies a low-pass effect to the audio, whereby only low frequencies can pass,
    effectively cutting off high frequencies meaning more emphasis is put on lower frequencies.
    """
    def __init__(self):
        super().__init__({'smoothing': 20.0})

    def update(self, **kwargs):
        """
        Note
        ----
        The limits are:

            1 < smoothing

        Parameters
        ----------
        smoothing: :class:`float`
            The strength of the effect.
        """
        if 'smoothing' in kwargs:
            smoothing = float(kwargs.pop('smoothing'))

            if smoothing <= 1:
                raise ValueError('smoothing must be bigger than 1')

            self.values['smoothing'] = smoothing

    def serialize(self) -> dict:
        return {'lowPass': self.values}


class ChannelMix(Filter):
    """
    Allows passing the audio from one channel to the other, or isolating individual
    channels.
    """
    def __init__(self):
        super().__init__({'leftToLeft': 1.0, 'leftToRight': 0.0, 'rightToLeft': 0.0, 'rightToRight': 1.0})

    def update(self, **kwargs):
        """
        Note
        ----
        The limits are:

            0 ≤ leftToLeft ≤ 1.0

            0 ≤ leftToRight ≤ 1.0

            0 ≤ rightToLeft ≤ 1.0

            0 ≤ rightToRight ≤ 1.0

        Parameters
        ----------
        left_to_left: :class:`float`
            The volume level of the audio going from the "Left" channel to the "Left" channel.
        left_to_right: :class:`float`
            The volume level of the audio going from the "Left" channel to the "Right" channel.
        right_to_left: :class:`float`
            The volume level of the audio going from the "Right" channel to the "Left" channel.
        right_to_right: :class:`float`
            The volume level of the audio going from the "Right" channel to the "Left" channel.
        """
        if 'left_to_left' in kwargs:
            left_to_left = float(kwargs.pop('left_to_left'))

            if not 0 <= left_to_left <= 1:
                raise ValueError('left_to_left must be bigger than or equal to 0, and less than or equal to 1.')

            self.values['leftToLeft'] = left_to_left

        if 'left_to_right' in kwargs:
            left_to_right = float(kwargs.pop('left_to_right'))

            if not 0 <= left_to_right <= 1:
                raise ValueError('left_to_right must be bigger than or equal to 0, and less than or equal to 1.')

            self.values['leftToRight'] = left_to_right

        if 'right_to_left' in kwargs:
            right_to_left = float(kwargs.pop('right_to_left'))

            if not 0 <= right_to_left <= 1:
                raise ValueError('right_to_left must be bigger than or equal to 0, and less than or equal to 1.')

            self.values['rightToLeft'] = right_to_left

        if 'right_to_right' in kwargs:
            right_to_right = float(kwargs.pop('right_to_right'))

            if not 0 <= right_to_right <= 1:
                raise ValueError('right_to_right must be bigger than or equal to 0, and less than or equal to 1.')

            self.values['rightToRight'] = right_to_right

    def serialize(self) -> dict:
        return {'channelMix': self.values}


class Distortion(Filter):
    """
    As the name suggests, this distorts the audio.
    """
    def __init__(self):
        super().__init__({'sinOffset': 0.0, 'sinScale': 1.0, 'cosOffset': 0.0, 'cosScale': 1.0,
                          'tanOffset': 0.0, 'tanScale': 1.0, 'offset': 0.0, 'scale': 1.0})

    def update(self, **kwargs):
        """
        Parameters
        ----------
        sin_offset: :class:`float`
            The sin offset.
        sin_scale: :class:`float`
            The sin scale.
        cos_offset: :class:`float`
            The sin offset.
        cos_scale: :class:`float`
            The sin scale.
        tan_offset: :class:`float`
            The sin offset.
        tan_scale: :class:`float`
            The sin scale.
        offset: :class:`float`
            The sin offset.
        scale: :class:`float`
            The sin scale.
        """
        if 'sin_offset' in kwargs:
            self.values['sinOffset'] = float(kwargs.pop('sin_offset'))

        if 'sin_scale' in kwargs:
            self.values['sinScale'] = float(kwargs.pop('sin_scale'))

        if 'cos_offset' in kwargs:
            self.values['cosOffset'] = float(kwargs.pop('cos_offset'))

        if 'cos_scale' in kwargs:
            self.values['cosScale'] = float(kwargs.pop('cos_scale'))

        if 'tan_offset' in kwargs:
            self.values['tanOffset'] = float(kwargs.pop('tan_offset'))

        if 'tan_scale' in kwargs:
            self.values['tanScale'] = float(kwargs.pop('tan_scale'))

        if 'offset' in kwargs:
            self.values['offset'] = float(kwargs.pop('offset'))

        if 'scale' in kwargs:
            self.values['scale'] = float(kwargs.pop('scale'))

    def serialize(self) -> dict:
        return {'distortion': self.values}
