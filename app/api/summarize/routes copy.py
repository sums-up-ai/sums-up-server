from fastapi import APIRouter, WebSocket, WebSocketDisconnect

summarize_router = APIRouter(tags=['summarize'])

@summarize_router.websocket("/ws/summarize")
async def websocket_summarize(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_text()
            await websocket.send_text(f"Summary of '{data}'")
        except Exception as e:
            print(f"Error: {e}")
            break