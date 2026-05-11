"""WebSocket chat handler with room/group support."""

from kewe import WebSocketManager, WebSocketConnection

manager = WebSocketManager()


async def chat_handler(ws: WebSocketConnection):
    """WebSocket chat with room support.
    Send: {"text": "hello"} for global broadcast
    Send: {"join": "room-name"} to join a room
    Send: {"to_group": {"room": "room-name", "text": "hello"}} for group message
    Send: {"leave": "room-name"} to leave a room
    """
    await ws.accept()
    conn_id = manager.add(ws)
    await manager.broadcast({"type": "join", "message": f"User {conn_id[:8]} joined"})
    try:
        async for message in ws:
            data = message.json()

            if "join" in data:
                room = data["join"]
                manager.join_group(conn_id, room)
                await ws.send_json({"type": "system", "message": f"Joined room '{room}'"})
            elif "leave" in data:
                room = data["leave"]
                manager.leave_group(conn_id, room)
                await ws.send_json({"type": "system", "message": f"Left room '{room}'"})
            elif "to_group" in data:
                gd = data["to_group"]
                room = gd.get("room", "")
                text = gd.get("text", "")
                if room and text:
                    msg = {"type": "group_message", "room": room, "data": {"text": text, "from": conn_id[:8]}}
                    await manager.broadcast_to_group(room, msg)
            else:
                await manager.broadcast({"type": "message", "data": data})
    finally:
        manager.remove(conn_id)
        await manager.broadcast({"type": "leave", "message": f"User {conn_id[:8]} left"})
