import logging
from app.api.histroy.handler import get_history_handler
from app.core.firebase import verify_token
from app.schemas.user import User
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


history_router = APIRouter(tags=['history'])

@history_router.get("/")
async def get_history(
    user: User = Depends(verify_token),
):
    try:
        histories = await get_history_handler(user.uid)
        if not histories:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=[]
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=histories
        )
    
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )