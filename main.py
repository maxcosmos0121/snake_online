# server.py
import socketio
from fastapi import FastAPI
import uvicorn

# 创建一个 Async Socket.IO 服务器
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()
app.mount("/", socketio.ASGIApp(sio, other_asgi_app=app))

# 在线人数记录
connected_users = set()

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    connected_users.add(sid)
    await sio.emit("user_count", {"count": len(connected_users)})

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    connected_users.discard(sid)
    await sio.emit("user_count", {"count": len(connected_users)})

@sio.event
async def chat(sid, data):
    print(f"{sid} says: {data}")
    await sio.emit("chat", {"sid": sid, "message": data}, skip_sid=sid)

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
