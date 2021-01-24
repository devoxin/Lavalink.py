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
        super().__init__([1.0] * 15)

    def update(self, **kwargs):
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
        return {'equalizer': [{'band': band, 'gain': gain} for band, gain in self.values]}


class Karaoke(Filter):
    def __init__(self):
        super().__init__({'level': 1.0, 'monoLevel': 1.0, 'filterBand': 220.0, 'filterWidth': 100.0})

    def update(self, **kwargs):
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
