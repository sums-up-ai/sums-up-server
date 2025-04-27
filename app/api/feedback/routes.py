import logging
from app.api.feedback.handler import create_feedback_handler
from app.api.feedback.schemas import FeedbackRequest
from fastapi import APIRouter, HTTPException, Depends, status
from app.core.firebase import verify_token
from app.schemas.user import User
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

feedback_router = APIRouter(tags=['feedback'])


@feedback_router.post("/submit")
async def submit_feedback(
    request: FeedbackRequest,
    user: User = Depends(verify_token),
):
    try:
        await create_feedback_handler(
            sessionId=request.sessionId,
            feedback=request.feedback
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content="Feedback submitted successfully."
        )
    
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )
