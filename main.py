# main.py

import socketio
from fastapi import FastAPI
import uvicorn
from socket_events import register_events  # 引入事件注册函数

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = FastAPI()

# 注册事件
register_events(sio)

# 包裹 FastAPI 应用
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == '__main__':
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
