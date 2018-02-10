class Utils:

    @staticmethod
    def format_time(time):
        """ Formats the given time into HH:MM:SS """
        seconds = (time / 1000) % 60
        minutes = (time / (1000 * 60)) % 60
        hours = (time / (1000 * 60 * 60)) % 24
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
