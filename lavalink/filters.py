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
# Necessary evil due to documenting filter update kwargs.
# At least, until I can come up with a better solution to doing this.
# pylint: disable=arguments-differ

from typing import Any, Dict, List, Tuple, overload

from .abc import Filter
from .common import MISSING


class Volume(Filter[float]):
    """
    Adjusts the audio output volume.
    """
    def __init__(self, volume: float = 1.0):
        super().__init__(volume)

    def update(self, *, volume: float):  # type: ignore
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
        volume = float(volume)

        if not 0 <= volume <= 5:
            raise ValueError('volume must be bigger than or equal to 0, and less than or equal to 5.')

        self.values = volume

    def serialize(self) -> Dict[str, float]:
        return {'volume': self.values}


class Equalizer(Filter[List[float]]):
    """
    Allows modifying the gain of 15 bands, to boost or reduce the volume of specific frequency ranges.
    For example, this could be used to boost the low (bass) frequencies to act as a 'bass boost'.
    """
    def __init__(self, gains: List[float] = MISSING):
        super().__init__([0.0] * 15 if gains is MISSING else gains)

    @overload
    def update(self, *, bands: List[Tuple[int, float]]):
        ...

    @overload
    def update(self, *, band: int, gain: int):
        ...

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

        Raises
        ------
        :class:`ValueError`
        """
        if 'bands' in kwargs:
            bands = kwargs.pop('bands')

            sanity_check = isinstance(bands, list) and all(isinstance(pair, tuple) for pair in bands) and \
                all(isinstance(band, int) and isinstance(gain, (float, int)) for band, gain in bands) and \
                all(0 <= band <= 14 and -0.25 <= gain <= 1.0 for band, gain in bands)

            if not sanity_check:
                raise ValueError('Bands must be a list of tuple representing (band: int, gain: float) with values between '
                                 '0 to 14, and -0.25 to 1.0 respectively')

            for band, gain in bands:
                self.values[band] = gain
        elif 'band' in kwargs and 'gain' in kwargs:
            band = int(kwargs.pop('band'))
            gain = float(kwargs.pop('gain'))

            if not 0 <= band <= 14:
                raise ValueError('Band must be between 0 and 14 (start and end inclusive)')

            if not -0.25 <= gain <= 1.0:
                raise ValueError('Gain must be between -0.25 and 1.0 (start and end inclusive)')

            self.values[band] = gain
        else:
            raise KeyError('Expected parameter bands OR band and gain, but neither were provided')

    def serialize(self) -> Dict[str, Any]:
        return {'equalizer': [{'band': band, 'gain': gain} for band, gain in enumerate(self.values)]}


class Karaoke(Filter[Dict[str, float]]):
    """
    Allows for isolating a frequency range (commonly, the vocal range).
    Useful for karaoke/sing-along.
    """
    def __init__(self, level: float = 1.0, mono_level: float = 1.0,
                 filter_band: float = 220.0, filter_width: float = 100.0):
        super().__init__({'level': level, 'monoLevel': mono_level, 'filterBand': filter_band, 'filterWidth': filter_width})

    @overload
    def update(self, *, level: float):
        ...

    @overload
    def update(self, *, mono_level: float):
        ...

    @overload
    def update(self, *, filter_band: float):
        ...

    @overload
    def update(self, *, filter_width: float):
        ...

    @overload
    def update(self, *, level: float, mono_level: float):
        ...

    @overload
    def update(self, *, level: float, filter_width: float):
        ...

    @overload
    def update(self, *, level: float, filter_band: float):
        ...

    @overload
    def update(self, *, mono_level: float, filter_width: float):
        ...

    @overload
    def update(self, *, mono_level: float, filter_band: float):
        ...

    @overload
    def update(self, *, filter_band: float, filter_width: float):
        ...

    @overload
    def update(self, *, level: float, mono_level: float, filter_width: float):
        ...

    @overload
    def update(self, *, level: float, mono_level: float, filter_band: float):
        ...

    @overload
    def update(self, *, level: float, mono_level: float, filter_band: float, filter_width: float):
        ...

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

        Raises
        ------
        :class:`ValueError`
        """
        if 'level' in kwargs:
            self.values['level'] = float(kwargs.pop('level'))

        if 'mono_level' in kwargs:
            self.values['monoLevel'] = float(kwargs.pop('mono_level'))

        if 'filter_band' in kwargs:
            self.values['filterBand'] = float(kwargs.pop('filter_band'))

        if 'filter_width' in kwargs:
            self.values['filterWidth'] = float(kwargs.pop('filter_width'))

    def serialize(self) -> Dict[str, Dict[str, float]]:
        return {'karaoke': self.values}


class Timescale(Filter[Dict[str, float]]):
    """
    Allows speeding up/slowing down the audio, adjusting the pitch and playback rate.
    """
    def __init__(self, speed: float = 1.0, pitch: float = 1.0, rate: float = 1.0):
        super().__init__({'speed': speed, 'pitch': pitch, 'rate': rate})

    @overload
    def update(self, *, speed: float):
        ...

    @overload
    def update(self, *, pitch: float):
        ...

    @overload
    def update(self, *, rate: float):
        ...

    @overload
    def update(self, *, speed: float, pitch: float):
        ...

    @overload
    def update(self, *, speed: float, rate: float):
        ...

    @overload
    def update(self, *, rate: float, pitch: float):
        ...

    @overload
    def update(self, *, speed: float, rate: float, pitch: float):
        ...

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

        Raises
        ------
        :class:`ValueError`
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

    def serialize(self) -> Dict[str, Dict[str, float]]:
        return {'timescale': self.values}


class Tremolo(Filter[Dict[str, float]]):
    """
    Applies a 'tremble' effect to the audio.
    """
    def __init__(self, frequency: float = 2.0, depth: float = 0.5):
        super().__init__({'frequency': frequency, 'depth': depth})

    @overload
    def update(self, *, frequency: float):
        ...

    @overload
    def update(self, *, depth: float):
        ...

    @overload
    def update(self, *, frequency: float, depth: float):
        ...

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

        Raises
        ------
        :class:`ValueError`
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

    def serialize(self) -> Dict[str, Dict[str, float]]:
        return {'tremolo': self.values}


class Vibrato(Filter[Dict[str, float]]):
    """
    Applies a 'wobble' effect to the audio.
    """
    def __init__(self, frequency: float = 2.0, depth: float = 0.5):
        super().__init__({'frequency': frequency, 'depth': depth})

    @overload
    def update(self, *, frequency: float):
        ...

    @overload
    def update(self, *, depth: float):
        ...

    @overload
    def update(self, *, frequency: float, depth: float):
        ...

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

        Raises
        ------
        :class:`ValueError`
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

    def serialize(self) -> Dict[str, Dict[str, float]]:
        return {'vibrato': self.values}


class Rotation(Filter[float]):
    """
    Phases the audio in and out of the left and right channels in an alternating manner.
    This is commonly used to create the 8D effect.
    """
    def __init__(self, rotation_hz: float = 0.0):
        super().__init__(rotation_hz)

    def update(self, *, rotation_hz: float):  # type: ignore
        """
        Note
        ----
        The limits are:

            0 ≤ rotation_hz

        Parameters
        ----------
        rotation_hz: :class:`float`
            How frequently the effect should occur.

        Raises
        ------
        :class:`ValueError`
        """
        rotation_hz = float(rotation_hz)

        if rotation_hz < 0:
            raise ValueError('rotation_hz must be bigger than or equal to 0')

        self.values = rotation_hz

    def serialize(self) -> Dict[str, Dict[str, float]]:  # type: ignore
        return {'rotation': {'rotationHz': self.values}}


class LowPass(Filter[float]):
    """
    Applies a low-pass effect to the audio, whereby only low frequencies can pass,
    effectively cutting off high frequencies meaning more emphasis is put on lower frequencies.
    """
    def __init__(self, smoothing: float = 20.0):
        super().__init__(smoothing)

    def update(self, *, smoothing: float):  # type: ignore
        """
        Note
        ----
        The limits are:

            1 < smoothing

        Parameters
        ----------
        smoothing: :class:`float`
            The strength of the effect.

        Raises
        ------
        :class:`ValueError`
        """
        smoothing = float(smoothing)

        if smoothing <= 1:
            raise ValueError('smoothing must be bigger than 1')

        self.values = smoothing

    def serialize(self) -> Dict[str, Dict[str, float]]:  # type: ignore
        return {'lowPass': {'smoothing': self.values}}


class ChannelMix(Filter[Dict[str, float]]):
    """
    Allows passing the audio from one channel to the other, or isolating individual
    channels.
    """
    def __init__(self, left_to_left: float = 1.0, left_to_right: float = 0.0,
                 right_to_left: float = 0.0, right_to_right: float = 0.0):
        super().__init__({'leftToLeft': left_to_left, 'leftToRight': left_to_right,
                          'rightToLeft': right_to_left, 'rightToRight': right_to_right})

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

        Raises
        ------
        :class:`ValueError`
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

    def serialize(self) -> Dict[str, Dict[str, float]]:
        return {'channelMix': self.values}


class Distortion(Filter[Dict[str, float]]):
    """
    As the name suggests, this distorts the audio.
    """
    def __init__(self, sin_offset: float = 0.0, sin_scale: float = 1.0, cos_offset: float = 0.0,
                 cos_scale: float = 1.0, tan_offset: float = 0.0, tan_scale: float = 1.0, offset: float = 0.0,
                 scale: float = 1.0):
        super().__init__({'sinOffset': sin_offset, 'sinScale': sin_scale, 'cosOffset': cos_offset, 'cosScale': cos_scale,
                          'tanOffset': tan_offset, 'tanScale': tan_scale, 'offset': offset, 'scale': scale})

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

        Raises
        ------
        :class:`ValueError`
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

    def serialize(self) -> Dict[str, Dict[str, float]]:
        return {'distortion': self.values}
