from pydantic import BaseModel, Field, conint, constr

class Feedback(BaseModel):
    ease: str
    speed: str
    grammar: str
    features: str
    otherFeedback: str

class FeedbackRequest(BaseModel):
    sessionId: str
    feedback: Feedback