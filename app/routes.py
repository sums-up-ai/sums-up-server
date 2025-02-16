from fastapi import FastAPI
from app.api.system.routes import system_router
from app.api.video.routes import video_router
from app.api.summarize import summarize_router

def register_routes(app: FastAPI):
    app.include_router(system_router, prefix="/api/system")
    app.include_router(video_router, prefix="/api/video")
    app.include_router(summarize_router, prefix="/api/summarize")

