from typing import Optional
from pydantic import BaseModel, Field, conint, constr

class SummarizeRequest(BaseModel):
    text: constr(min_length=100, max_length=5000) = Field(..., description="Text to summarize")
    min_length: conint(ge=30, le=150) = 30 # type: ignore
    max_length: conint(ge=50, le=250) = 150 # type: ignore

class SummarizeSessionRequest(BaseModel):
    videoId: str
    title: str
    channelName: str
    thumbnailUrl: str

class SessionData(BaseModel):
    sessionId: str
    uid: str
    videoId: str
    title: str
    channelName: str
    thumbnailUrl: str
    createdAt: str
    status: str