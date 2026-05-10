"""WebSocket chat handler."""

from kewe import WebSocketManager, WebSocketConnection

manager = WebSocketManager()


async def chat_handler(ws: WebSocketConnection):
    await ws.accept()
    manager.connect(ws)
    try:
        await manager.broadcast({"type": "join", "message": "A user joined the chat"})
        async for message in ws:
            data = message.json()
            await manager.broadcast({"type": "message", "data": data})
    finally:
        manager.disconnect(ws)
        await manager.broadcast({"type": "leave", "message": "A user left the chat"})
