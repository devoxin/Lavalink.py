def format_time(time):
    """
    Formats the given time into HH:MM:SS.
    ----------
    :param time:
        The time in milliseconds
    """
    hours, remainder = divmod(time / 1000, 3600)
    minutes, seconds = divmod(remainder, 60)

    return '%02d:%02d:%02d' % (hours, minutes, seconds)
