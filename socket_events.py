import uuid
from datetime import datetime
import asyncio

connected_users = set()
rooms = {}  # room_id -> {name, status, created_at, owner, users: [sid]}
lock = asyncio.Lock()


def get_room_info(room_id):
    room = rooms.get(room_id)
    if not room:
        return None
    return {
        "room": room_id,
        "name": room["name"],
        "status": room["status"],
        "created_at": room["created_at"],
        "owner": room["owner"],
        "user_count": len(room["users"]),
    }


async def broadcast_room_list(sio):
    async with lock:
        room_list = [
            {
                "room": room_id,
                "name": info["name"],
                "status": info["status"],
                "created_at": info["created_at"],
                "owner": info["owner"],
                "user_count": len(info["users"]),
            }
            for room_id, info in rooms.items()
        ]
    await sio.emit("room_list_update", {"rooms": room_list})


async def broadcast_user_count(sio):
    await sio.emit("user_count", {"count": len(connected_users)})


def register_events(sio):
    # ============================== 游戏相关 ==============================
    @sio.event
    async def connect(sid, environ):
        async with lock:
            connected_users.add(sid)
        join_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{join_time} [{sid}] 加入游戏 当前在线人数 {len(connected_users)}")
        await broadcast_user_count(sio)

    @sio.event
    async def disconnect(sid):
        async with lock:
            connected_users.discard(sid)
            # 从所有房间中移除该用户
            for room_id, info in list(rooms.items()):
                if sid in info["users"]:
                    info["users"].remove(sid)
                    await sio.leave_room(sid, room_id)
                    print(f"{datetime.now()} [{sid}] 离开房间 [{room_id}]")
                    # 如果房间为空则删除
                    if not info["users"]:
                        del rooms[room_id]
                        print(f"{datetime.now()} 房间 [{room_id}] 已被清空并删除")

        print(f"{datetime.now()} [{sid}] 离开游戏 当前在线人数 {len(connected_users)}")
        await broadcast_room_list(sio)
        await broadcast_user_count(sio)

    @sio.event
    async def get_user_count(sid):
        await sio.emit("user_count", {"count": len(connected_users)}, to=sid)

    # ============================== 房间相关 ==============================
    @sio.event
    async def create_room(sid, data):
        username = data.get("username")
        room_name = data.get("room_name", "默认房间")

        if not username:
            await sio.emit("error", {"message": "用户名不能为空"}, to=sid)
            return

        async with lock:
            while True:
                room_id = str(uuid.uuid4())[:8]
                if room_id not in rooms:
                    break

            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rooms[room_id] = {
                "name": room_name,
                "status": "未开始",
                "created_at": created_at,
                "owner": username,
                "users": [sid],
            }

        await sio.enter_room(sid, room_id)

        print(f"{created_at} [{username}] 创建了房间 [{room_id}]")

        await sio.emit("room_created", {
            "room": room_id,
            "username": username,
            "room_info": get_room_info(room_id),
        }, to=sid)

        await broadcast_room_list(sio)

    @sio.event
    async def join_room(sid, data):
        room_id = data.get("room")
        username = data.get("username")

        if not room_id:
            await sio.emit("error", {"message": "房间号不能为空"}, to=sid)
            return
        if not username:
            await sio.emit("error", {"message": "用户名不能为空"}, to=sid)
            return

        async with lock:
            if room_id not in rooms:
                await sio.emit("error", {"message": "房间不存在"}, to=sid)
                return

            if sid not in rooms[room_id]["users"]:
                rooms[room_id]["users"].append(sid)

        await sio.enter_room(sid, room_id)

        join_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{join_time} [{username}] 加入了房间 [{room_id}]")

        await sio.emit("system_join_room", {
            "message": f"{join_time} [{username}] 加入了房间 [{room_id}]"
        }, room=room_id)

        await sio.emit("room_info", get_room_info(room_id), to=sid)
        await broadcast_room_list(sio)

    @sio.event
    async def leave_room(sid, data):
        room_id = data.get("room")
        username = data.get("username")

        if not room_id or not username:
            await sio.emit("error", {"message": "房间号或用户名不能为空"}, to=sid)
            return

        async with lock:
            if room_id not in rooms:
                await sio.emit("error", {"message": "房间不存在"}, to=sid)
                return

            if sid in rooms[room_id]["users"]:
                rooms[room_id]["users"].remove(sid)
                # 如果房间清空了就删掉
                if not rooms[room_id]["users"]:
                    del rooms[room_id]
                    print(f"{datetime.now()} 房间 [{room_id}] 已被清空并删除")

        await sio.leave_room(sid, room_id)

        leave_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{leave_time} [{username}] 离开了房间 [{room_id}]")

        await sio.emit("system_leave_room", {
            "message": f"{leave_time} [{username}] 离开了房间 [{room_id}]"
        }, room=room_id)

        await broadcast_room_list(sio)

    @sio.event
    async def list_rooms(sid):
        await broadcast_room_list(sio)
