from pydantic import BaseModel, Field, conint, constr

class SummarizeRequest(BaseModel):
    text: constr(min_length=100, max_length=5000) = Field(..., description="Text to summarize") # type: ignore
    min_length: conint(ge=30, le=150) = 30 # type: ignore
    max_length: conint(ge=50, le=250) = 150 # type: ignore
