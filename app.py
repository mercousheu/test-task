import asyncio
import math
from datetime import datetime
from json import JSONDecodeError

from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint, HTTPEndpoint
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.templating import Jinja2Templates

user_states = {}
templates = Jinja2Templates(directory='templates')


class Homepage(HTTPEndpoint):
    async def get(self, request):
        return templates.TemplateResponse('home.html', {'request': request})

    async def post(self, request):
        try:
            payload = await request.json()
            key = payload['wsKey']
            user_states[key]['state'] = 'stop'
            user_states[key]['stop_time'] = datetime.now()
            return JSONResponse({'OK': 'stopped'}, status_code=200)
        except JSONDecodeError:
            response = JSONResponse({'Error': 'Invalid JSON'}, status_code=400)
        return response


class Start(WebSocketEndpoint):
    encoding = "json"

    def get_security_key(self):
        headers = {x[0].decode(encoding='utf-8'): x[1].decode(encoding='utf-8') for x in self.scope['headers']}
        key = headers.get('sec-websocket-key')
        return key

    async def on_connect(self, websocket):
        key = self.get_security_key()
        if key:
            await websocket.accept()
            user_states[key] = {}
            await websocket.send_json({'user_key': key})
        else:
            await websocket.close()

    async def on_receive(self, websocket, data):
        key = self.get_security_key()
        start_time = datetime.now()
        user_states[key] = {'state': 'start', 'start_time': start_time, 'timer': 0}
        while True:
            if user_states[key]['state'] == 'start':
                await asyncio.sleep(0.5)
                user_states[key]['timer'] += 0.5
                await websocket.send_json({'timer': math.floor(user_states[key]['timer'])})
            else:
                break

    async def on_disconnect(self, websocket, close_code):
        key = self.get_security_key()
        del user_states[key]


routes = [
    Route("/", Homepage),
    WebSocketRoute("/start", Start),
]

app = Starlette(routes=routes)
