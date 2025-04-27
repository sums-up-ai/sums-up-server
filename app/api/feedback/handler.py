from app.api.feedback.schemas import Feedback
from app.services.firebase import firestore
from app.services.firebase.firestore import Firestore

store = Firestore(collection_name="ext_summarize")

async def create_feedback_handler(
    sessionId: str, 
    feedback: Feedback
):
   await store.update(sessionId, {
       "feedback": feedback.dict()
   })
   return sessionId