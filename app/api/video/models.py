from pydantic import BaseModel

class VideoRequest(BaseModel):
    videoId: str