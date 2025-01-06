from fastapi import FastAPI
from app.api import video

app = FastAPI()

app.include_router(video.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



# from fastapi import FastAPI, WebSocket, HTTPException

# app = FastAPI()

# @app.get("/items/{item_id}")
# async def read_item(item_id: int):
#     if item_id == 0:
#         raise HTTPException(status_code=404, detail="Item not found")
#     return {"item_id": item_id, "name": "Item name"}

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     while True:
#         data = await websocket.receive_text()
#         await websocket.send_text(f"Message received: {data}")