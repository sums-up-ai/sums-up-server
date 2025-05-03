import logging
from app.api.histroy.handler import delete_all_history_by_uid_handler, delete_history_by_id_handler, get_history_by_id_handler, get_history_handler
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
    
@history_router.get("/{sessionId}")
async def get_history_by_id(
    sessionId: str,
    user: User = Depends(verify_token),
):
    try:
        history = await get_history_by_id_handler(sessionId)
        if not history:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={}
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=history
        )
    
    except Exception as e:
        logger.error(f"Error getting history by ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history by ID: {str(e)}"
        )
    
@history_router.delete("/delete-all")
async def delete_all_history_by_uid(
    user: User = Depends(verify_token),
):
    try:
        result = await delete_all_history_by_uid_handler(user.uid)
        if not result:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "No history found to delete"}
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "All history deleted successfully"}
        )
        
    
    except Exception as e:
        logger.error(f"Error deleting all history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete all history: {str(e)}"
        )    

@history_router.delete("/delete/{sessionId}")
async def delete_history_by_id(
    sessionId: str,
    user: User = Depends(verify_token),
):
    try:
        result = await delete_history_by_id_handler(sessionId)
        if not result:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "No history found to delete"}
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "History deleted successfully"}
        )
        
    
    except Exception as e:
        logger.error(f"Error deleting history by ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete history by ID: {str(e)}"
        )