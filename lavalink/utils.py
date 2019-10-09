import warnings


def format_time(time):
    """
    Formats the given time into HH:MM:SS.

    Parameters
    ----------
    time: :class:`int`
        The time in milliseconds.
    """
    hours, remainder = divmod(time / 1000, 3600)
    minutes, seconds = divmod(remainder, 60)

    return '%02d:%02d:%02d' % (hours, minutes, seconds)


def parse_time(time):
    """
    Parses the given time into days, hours, minutes and seconds.
    Useful for formatting time yourself.

    Parameters
    ----------
    time: :class:`int`
        The time in milliseconds.
    """
    days, remainder = divmod(time / 1000, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    return days, hours, minutes, seconds


def deprecated(message):
    def deprecated_decorator(func):
        def deprecated_func(*args, **kwargs):
            warnings.warn('{} is a deprecated function. {}'.format(func.__name__, message),
                          category=DeprecationWarning,
                          stacklevel=2)
            warnings.simplefilter('default', DeprecationWarning)
            return func(*args, **kwargs)
        return deprecated_func
    return deprecated_decorator
