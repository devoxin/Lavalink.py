import discord
import websockets
import asyncio
import threading


class Client:
    def __init__(self, shard_count, user_id, password='', host='localhost', port=80, loop=asyncio.get_event_loop()):
        self.loop = loop
        self.shard_count = shard_count
        self.user_id = user_id
        self.password = password
        self.host = host
        self.port = port
        self.uri = f'ws://{host}:{port}'

        loop.run_until_complete(self.connect())
    
    async def connect(self):
        headers = {
            'Authorization': self.password,
            'Num-Shards': self.shard_count,
            'User-Id': self.user_id
        }
        try:
            print("connecting!")
            self.ws = await websockets.connect(self.uri, extra_headers=headers)
            self.dispatcher = asyncio.ensure_future(self.ws_listen())
            print("connected!")
        except Exception as e:
            raise e from None
            
    async def ws_listen(self):
        while True:
            data = await self.ws.recv()
            await dispatch(data)
    
    async def dispatch(data):
        print(data)

    async def send(data):
        print("todo")

if __name__ == '__main__':
    a = Client(shard_count=1, user_id=0, password='youshallnotpass')
