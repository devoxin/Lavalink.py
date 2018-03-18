def format_time(time):
    """ Formats the given time into HH:MM:SS """
    h, r = divmod(time / 1000, 3600)
    m, s = divmod(r, 60)

    return "%02d:%02d:%02d" % (h, m, s)
