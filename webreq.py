import aiohttp
import asyncio

pool = aiohttp.ClientSession()


async def get(url, jsonify=False, *args, **kwargs):
    try:
        async with pool.get(url, *args, **kwargs) as r:
            if r.status != 200:
                return None

            if jsonify:
                return await r.json(content_type=None)

            return await r.read()
    except (aiohttp.ClientOSError, aiohttp.ClientConnectorError, asyncio.TimeoutError):
        return None
