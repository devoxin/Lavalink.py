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
