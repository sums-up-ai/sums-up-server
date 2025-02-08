from fastapi import WebSocket, WebSocketDisconnect

# class WebSocketManager:
#     def __init__(self):
#         self.active_connections: dict[str, list[WebSocket]] = {}

#     async def connect(self, ws_id: str, websocket: WebSocket):
#         await websocket.accept()
#         if ws_id not in self.active_connections:
#             self.active_connections[ws_id] = []
#         self.active_connections[ws_id].append(websocket)
#         print(f"WebSocket {ws_id} connected. Total connections: {len(self.active_connections[ws_id])}")

#     def disconnect(self, ws_id: str, websocket: WebSocket):
#         if ws_id in self.active_connections:
#             self.active_connections[ws_id].remove(websocket)
#             if not self.active_connections[ws_id]:
#                 del self.active_connections[ws_id]
#             print(f"WebSocket {ws_id} disconnected. Remaining connections: {len(self.active_connections.get(ws_id, []))}")

#     async def send_message_to(self, ws_id: str, message: str):
#         if ws_id in self.active_connections:
#             for connection in self.active_connections[ws_id]:
#                 await connection.send_text(message)

#     async def broadcast(self, message: str):
#         for connections in self.active_connections.values():
#             for connection in connections:
#                 await connection.send_text(message)


class WSConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: str, user_id: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_text(message)
