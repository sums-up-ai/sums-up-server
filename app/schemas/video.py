from pydantic import BaseModel

class VideoItem(BaseModel):
    videoId: str

class VideoResponse(BaseModel):
    message: str
