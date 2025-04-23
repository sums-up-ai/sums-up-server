from pydantic import BaseModel
from typing import Optional, Dict, Any

class UserMetadata(BaseModel):
    creation_timestamp: Optional[int]
    last_sign_in_timestamp: Optional[int]
    last_refresh_timestamp: Optional[int]

class User(BaseModel):
    uid: str
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    phone_number: Optional[str] = None
    provider_id: Optional[str] = None
    disabled: Optional[bool] = None
    custom_claims: Optional[Dict[str, Any]] = None
    user_metadata: Optional[Dict[str, Any]] = None
