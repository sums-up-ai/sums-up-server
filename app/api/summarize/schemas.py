from typing import Optional
from pydantic import BaseModel, Field, conint, constr

class SummarizeRequest(BaseModel):
    text: str

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