import aiohttp
import asyncio

class Requests:
    def __init__(self):
        self.pool = aiohttp.ClientSession()

    async def get(self, url, jsonify=False, *args, **kwargs):
        try:
            async with self.pool.get(url, *args, **kwargs) as r:
                if r.status != 200:
                    return None

                if jsonify:
                    return await r.json(content_type=None)

                return await r.read()
        except (aiohttp.ClientOSError, aiohttp.ClientConnectorError, asyncio.TimeoutError):
            return None

class IGeneric:
    def __init__(self):
        self.requester = None
        self.ws = None

class Utils:

    @staticmethod
    def format_time(time):
        seconds = (time / 1000) % 60
        minutes = (time / (1000 * 60)) % 60
        hours = (time / (1000 * 60 * 60)) % 24
        return "%02d:%02d:%02d" % (hours, minutes, seconds)

    @staticmethod
    def is_number(num):
        if num is None:
            return False

        try:
            int(num)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_number(num, default=1):
        if num is None:
            return default

        try:
            return int(num)
        except ValueError:
            return default

