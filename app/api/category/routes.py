import asyncio
from app.api.category.hander import predict_category_handler
from app.api.category.schemas import CategoryPredictionRequest
from app.core.firebase import verify_token
from app.core.verfiy_key import verify_dual_auth
from app.schemas.user import User
from app.services.firebase.firestore import Firestore
from app.services.model_dependencies.bert import get_bert_request_semaphore, get_sin_bert_model_and_tokenizer
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
import logging

store = Firestore(collection_name="ext_summarize")

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

session_store = {}

category_router = APIRouter(tags=['category'])

@category_router.post("/predict")
async def predict(
    request: CategoryPredictionRequest,
    user_or_key = Depends(verify_dual_auth),
    model_resources=Depends(get_sin_bert_model_and_tokenizer),
    semaphore=Depends(get_bert_request_semaphore),
):
    model, tokenizer, config = model_resources
    try:
        async with semaphore:
            label_probabilities, predicted_category = await predict_category_handler(
                text=request.text,
                model=model,
                tokenizer=tokenizer,
                config=config,
            )

            return JSONResponse(
                content={
                    "label_probabilities": label_probabilities,
                    "predicted_category": predicted_category,
                },
                status_code=status.HTTP_200_OK,
            )

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during summarization: {str(e)}",
        )