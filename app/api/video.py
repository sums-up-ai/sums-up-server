from fastapi import APIRouter, Depends
from app.schemas.video import VideoItem, VideoResponse
from app.services.video_service import VideoService

router = APIRouter()

@router.post("/video", response_model=VideoResponse)
async def process_video(item: VideoItem, service: VideoService = Depends(VideoService)):
    message = await service.process_video(item.videoId)
    return VideoResponse(message=message)
