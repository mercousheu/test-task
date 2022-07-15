import asyncio
import math
import datetime
import time
from json import JSONDecodeError

from databases import Database, DatabaseURL
from starlette.applications import Starlette
from starlette.endpoints import WebSocketEndpoint, HTTPEndpoint
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.templating import Jinja2Templates
from starlette.config import Config

config = Config(".env")
DATABASE_URL = config('DATABASE_URL', cast=DatabaseURL)
user_states = {}
templates = Jinja2Templates(directory='templates')


def create_response_dict(timestamp, timer, event):
    resp = {
        'timer': timer,
        'time_stamp': str(datetime.datetime.strftime(timestamp, '%d.%m.%Y %H:%M:%S')),
        'event': event
    }
    return resp


class Homepage(HTTPEndpoint):
    async def get(self, request):
        database = Database(DATABASE_URL)
        await database.connect()
        query = "select to_char(time_stamp, 'dd.mm.yyyy hh:mm:ss') as time_stamp, timer, event from results"
        rows = await database.fetch_all(query=query)
        await database.disconnect()
        return templates.TemplateResponse('home.html', {'request': request, 'rows': rows})

    async def post(self, request):
        try:
            payload = await request.json()
            key = payload['wsKey']
            user_states[key]['state'] = payload['event']

            database = Database(DATABASE_URL)
            await database.connect()

            select_query = "select timer from results where time_stamp = (select max(time_stamp) from results)"
            insert_query = "insert into results (time_stamp, timer, event) values (:timestamp, :timer, :event)"

            ret = await database.fetch_one(select_query)
            if ret and 'timer' in dict(ret):
                secs = sum(int(x) * 60 ** i for i, x in enumerate(reversed(dict(ret)['timer'].split(':'))))
            else:
                secs = 0
            if payload['event'] == 'start':
                timestamp = user_states[key]['start_time']
                timer = str(time.strftime('%H:%M:%S', time.gmtime(secs)))
            else:
                timestamp = user_states[key]['start_time'] + datetime.timedelta(seconds=payload['timer'])
                timer = str(time.strftime('%H:%M:%S', time.gmtime(secs + payload['timer'])))
            await database.execute(
                query=insert_query,
                values={'timestamp': timestamp, 'timer': timer, 'event': payload['event']}
            )
            await database.disconnect()
            return JSONResponse(create_response_dict(timestamp, timer, payload['event']), status_code=200)
        except (JSONDecodeError, KeyError, ValueError) as e:
            response = JSONResponse({'Error': str(e)}, status_code=400)
        return response


class Start(WebSocketEndpoint):
    encoding = "json"

    def get_security_key(self):
        headers = {
            x[0].decode(encoding='utf-8'): x[1].decode(encoding='utf-8') for x in self.scope['headers']
        }
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
        start_time = datetime.datetime.now()
        try:
            user_states[key] = {'state': 'start', 'start_time': start_time, 'timer': 0}
            while user_states[key]['state'] == 'start':
                await asyncio.sleep(0.5)
                user_states[key]['timer'] += 0.5
                timer = str(time.strftime('%H:%M:%S', time.gmtime(math.floor(user_states[key]['timer']))))
                await websocket.send_json(
                    create_response_dict(user_states[key]['start_time'], timer, user_states[key]['state'])
                )
        except KeyError as e:
            await websocket.send_json({'Error': e})

    async def on_disconnect(self, websocket, close_code):
        key = self.get_security_key()
        del user_states[key]


routes = [
    Route("/", Homepage),
    WebSocketRoute("/start", Start),
]

app = Starlette(routes=routes)

