from fastapi import FastAPI
from app.api.system.routes import system_router
from app.api.video.routes import video_router
from app.api.summarize import summarize_router
from app.api.test.routes import test_router
from app.api.histroy.routes import history_router
from app.api.feedback.routes import feedback_router
from app.api.category.routes import category_router

def register_routes(app: FastAPI):
    app.include_router(system_router, prefix="/api/system")
    app.include_router(video_router, prefix="/api/video")
    app.include_router(summarize_router, prefix="/api/summarize")
    app.include_router(test_router, prefix="/api/test")
    app.include_router(history_router, prefix="/api/history")
    app.include_router(feedback_router, prefix="/api/feedback")
    app.include_router(category_router, prefix="/api/category")

