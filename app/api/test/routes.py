from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any

from app.core.firebase import verify_token
from app.services.firebase.firestore import Firestore

test_router = APIRouter(tags=["test"])

test_collection = Firestore("test_collection")

class TestData(BaseModel):
    message: str
    value: int

@test_router.post("/save")
async def save_test_data(
    data: TestData,
    user_data: Dict[str, Any] = Depends(verify_token)
):
    user_id = user_data.get("uid")
    doc = data.dict()
    doc["user_id"] = user_id

    doc_id = await test_collection.create(doc)
    return {"status": "success", "doc_id": doc_id}
