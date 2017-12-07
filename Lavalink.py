import discord
import websockets
import asyncio


class Client():
    def __init__(self, shard_count, user_id, password='', host='localhost', port=80):
        self.shard_count = shard_count
        self.user_id = user_id
        self.password = password
        self.host = host
        self.port = port
        self.uri = f'ws://{host}:{port}'
        
        self.connect()
    
    def connect(self):
        headers = {
            'Authorization': self.password,
            'Num-Shards': self.shard_count,
            'User-Id': self.user_id
        }
        self.ws = await websockets.connect(self.uri, headers=headers)

        while True:
            data = await self.ws.recv()
            await dispatch(data)
    
    async def dispatch(data):
        print(data)

    async def send(data):
        print("todo")