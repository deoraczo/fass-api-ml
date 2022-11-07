from time import sleep
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import asyncio
from redis import Redis
import json
import uvicorn
import cv2
import base64

# https://gist.github.com/wshayes/8b0bf51397131c018d0e3f735eb02784

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <div>
            <img id="image" src='' >
        </div>
        <script>
            console.log('inicinado');
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                const image = document.getElementById('image');
                image.src = `data:image/jpeg;base64,${event.data}`;
                /*var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)*/
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

# class BackgroundRunner:
#     def __init__(self):
#         self.value = 0

#     async def run_main(self):
#         while True:
#             await asyncio.sleep(0.1)
#             self.value += 1

# runner = BackgroundRunner()

stream_key = 'tickets'
hostmane = 'localhost'
port = 6379
group = 'reader'

def connect_to_redis():
    r = Redis(hostmane, port, retry_on_timeout=True)
    return r

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
# redis = connect_to_redis()
# redis.xgroup_create(stream_key , group)
task = None


async def run_main():
    try:
        
        while True:
            print("reasssss")
            try:
                streams = redis.xreadgroup(group, "lslslsl", {stream_key: ">"}, count=1, block=0)
                print(streams)
                for stream in streams:
                    key, value = stream
                    id, data = value[0]
                    data_dict = {k.decode("utf-8"): data[k].decode("utf-8") for k in data}
                
                    d = json.loads(data_dict['data'])
                    # other = {data_dict['data'][k]: k for k in data_dict['data']}
                    await manager.broadcast(d['pix'])
                    redis.xdel(stream_key, id)
                # resp = redis_connection.xread(
                #     {stream_key: last_id}, count=1, block=sleep_ms
                # )
                # if resp:
                #     key, messages = resp[0]
                #     print(messages)
                #     last_id, data = messages[0]
                #     data_dict = {k.decode("utf-8"): data[k].decode("utf-8") for k in data}
                #     # print("REDIS ID: ", last_id)
                #     print("      --> ", data_dict['data'])

            except ConnectionError as e:
                print("ERROR REDIS CONNECTION: {}".format(e)) 
            
            await asyncio.sleep(1 / 100)
    except:
        print("Error por aca")
            
async def printer():
    await asyncio.sleep(5)
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    camera = cv2.VideoCapture("rtsp://admin:Inaigem1.1@200.48.171.237:554/dac/realplay/378843DD-8761-4BC9-8770-B1521267190E1/SUB/TCP?streamform=rtp")
    while True:
        _, img = camera.read()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        for (x, y, w, h) in faces:
            cv2.rectangle(img,(x,y), (x+w,y+h), (0,255,0), 2)
        _, buffer = cv2.imencode('.jpg', img)
        strs = base64.b64encode(buffer)
        # print(strs.decode("utf-8"))
        await manager.broadcast(strs.decode("utf-8"))
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    loop.create_task(printer())
    # loop.run_forever()
    # asyncio.create_task(printer())

@app.on_event("shutdown")
def shutdown_event():
    event_loop = asyncio.get_event_loop()
    event_loop.stop()
    

@app.get('/')
async def root():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)