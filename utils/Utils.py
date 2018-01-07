class Utils:

    @staticmethod
    def format_time(time):
        seconds = (time / 1000) % 60
        minutes = (time / (1000 * 60)) % 60
        hours = (time / (1000 * 60 * 60)) % 24
        return "%02d:%02d:%02d" % (hours, minutes, seconds)

    @staticmethod
    def is_number(obj):
        return isinstance(obj, int)

    @staticmethod
    def get_number(num, default=1):
        if num is None:
            return default

        try:
            return int(num)
        except ValueError:
            return default
