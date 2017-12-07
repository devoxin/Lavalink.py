import asyncio
import json

import discord
from . import webreq
import websockets


class Client:
    def __init__(self, bot, shard_count, user_id, password='', host='localhost', port=80, loop=asyncio.get_event_loop()):
        self.bot = bot
        self.loop = loop
        self.shard_count = shard_count
        self.user_id = user_id
        self.password = password
        self.host = host
        self.port = port
        self.uri = f'ws://{host}:{port}'

        loop.create_task(self.connect())
    
    async def connect(self):
        headers = {
            'Authorization': self.password,
            'Num-Shards': self.shard_count,
            'User-Id': self.user_id
        }
        try:
            self.ws = await websockets.connect(self.uri, extra_headers=headers)
            self.loop.create_task(self.listen())
            print("[WS] Ready")
        except Exception as e:
            raise e from None
    
    async def listen(self):
        while True:
            data = await self.ws.recv()
            j = json.loads(data)
            print("=== RECEIVE ===")
            print(j)

            if 'op' in j:
                if j.get('op') == 'validationReq':
                    await self.validate_connect(j)
                elif j.get('op') == 'isConnectedReq':
                    await self.validate_connection(j)
                elif j.get('op') == 'sendWS':
                    await self.bot._connection._get_websocket(330777295952543744).send(j.get('message'))

    async def send(self, data):
        print("=== SEND ===")
        print(data)
        payload = json.dumps(data)
        await self.ws.send(payload)

    async def get_tracks(self, query):
        headers = {
            'Authorization': self.password,
            'Accept': 'application/json'
        }
        return await webreq.get(f'http://{self.host}:2333/loadtracks?identifier={query}', jsonify=True, headers=headers)

    async def send_connect_request(self, ctx):
        payload = {
            'op': 'connect',
            'guildId': '330777295952543744',
            'channelId': '376117569096253440'
        }
        await self.send(payload)

    async def validate_connect(self, data):
        payload = {
            'op': 'validationRes',
            'guildId': '330777295952543744',
            'channelId': '376117569096253440',
            'valid': True
        }
        
        await self.send(payload)

    async def validate_connection(self, data):
        payload = {
            'op': 'isConnectedRes',
            'shardId': 0,
            'connected': True
        }
        await self.send(payload)
    
    async def play_track(self, ctx, track):
        payload = {
            'op': 'play',
            'guildId': '330777295952543744',
            'track': track['track']
        }
        await self.send(payload)
