def format_time(time):
    """
    Formats the given time into HH:MM:SS.
    ----------
    :param time:
        The time in milliseconds.
    """
    hours, remainder = divmod(time / 1000, 3600)
    minutes, seconds = divmod(remainder, 60)

    return '%02d:%02d:%02d' % (hours, minutes, seconds)


def parse_time(time):
    """
    Parses the given time into days, hours, minutes and seconds.
    Useful for formatting time yourself.
    ----------
    :param time:
        The time in milliseconds.
    """
    days, remainder = divmod(time / 1000, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    return days, hours, minutes, seconds
