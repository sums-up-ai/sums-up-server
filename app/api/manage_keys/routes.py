import logging
from app.api.manage_keys.handler import get_keys_handler, create_key_handler, revoke_key_handler
from app.core.firebase import verify_token
from app.schemas.user import User
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

manage_key_router = APIRouter(tags=['manage-keys'])

@manage_key_router.get("/")
async def get_keys(
    user: User = Depends(verify_token),
):
    try:
        keys = await get_keys_handler(user.uid)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=keys or []
        )
    except Exception as e:
        logger.error(f"Error getting keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get keys: {str(e)}"
        )

@manage_key_router.post("/")
async def create_key(
    user: User = Depends(verify_token),
):
    try:
        key = await create_key_handler(user.uid)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=key
        )
    except Exception as e:
        logger.error(f"Error creating key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create key: {str(e)}"
        )

@manage_key_router.delete("/revoke/{key_id}")
async def revoke_key(
    key_id: str,
    user: User = Depends(verify_token),
):
    try:
        result = await revoke_key_handler(key_id, user.uid)
        if not result:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "Key not found or not authorized"}
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Key revoked successfully"}
        )
    except Exception as e:
        logger.error(f"Error revoking key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke key: {str(e)}"
        )
