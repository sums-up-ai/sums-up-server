from app.core.path_utils import get_project_path
import firebase_admin
from firebase_admin import credentials, auth, firestore
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Dict, Any

cred = credentials.Certificate(get_project_path("credentials/firebase-admin-sdk.json"))
firebase_app = firebase_admin.initialize_app(cred)
db = firestore.client()

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    """Verify Firebase JWT token and return user information"""
    try:
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )