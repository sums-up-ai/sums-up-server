from fastapi import FastAPI
from app.api.system.routes import system_router
from app.api.video.routes import video_router

def register_routes(app: FastAPI):
    app.include_router(system_router, prefix="/api/system")
    app.include_router(video_router, prefix="/api/video")

