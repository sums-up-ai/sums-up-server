from fastapi import APIRouter, HTTPException, Depends
from app.api.video.models import VideoRequest
from app.api.video.service import VideoService

video_router = APIRouter(tags=["Video"])

@video_router.post("/generate-url", summary="Generate YouTube URL")
async def generate_video_url(request: VideoRequest):
    try:
        return VideoService.generate_youtube_url(request.videoId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
