from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.firebase import verify_token
from app.schemas.user import User
from app.services.firebase.firestore import Firestore
from typing import Union

security = HTTPBearer()
api_key_store = Firestore(collection_name="api_keys")

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    result = await api_key_store.get_by_field("key", token)
    if result:
        return {"api_key": token, "uid": result[0].get("uid")}
    return None

async def verify_dual_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Union[User, dict]:
    try:
        user = await verify_token(credentials)
        return user
    except HTTPException as e:
        if e.status_code != status.HTTP_401_UNAUTHORIZED:
            raise e

    api_key_info = await verify_api_key(credentials)
    if api_key_info:
        return api_key_info
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials (token or API key).",
        headers={"WWW-Authenticate": "Bearer"},
    )
