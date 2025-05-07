import asyncio
from app.api.category.hander import predict_category_handler
from app.api.summarize.handler import create_session_handler, generate_summary_with_category_handler, generate_summary_without_category_handler, generate_trascript_hander, generate_video_summary_handler, get_session_handler
from app.api.summarize.schemas import SummarizeSessionRequest, SummarizeWithCategoryRequest
from app.core.firebase import verify_token
from app.schemas.user import User
from app.services.firebase.firestore import Firestore
from app.services.model_dependencies.bert import get_sin_bert_model_and_tokenizer
from app.services.model_dependencies.mt5 import get_with_category_model_and_tokenizer
from app.services.post_processing.zero_with_char import postprocess_text
import torch
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from app.api.summarize import SummarizeRequest
from app.services.model_dependencies import get_model_and_tokenizer, get_request_semaphore
import logging

store = Firestore(collection_name="ext_summarize")

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

session_store = {}

summarize_router = APIRouter(tags=['summarize'])

@summarize_router.post("/create-session")
async def create_session(
    request: SummarizeSessionRequest,
    user: User = Depends(verify_token),
):
    try:
        session_id = await create_session_handler(request, user)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"session_id": session_id}
        )
    
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )

@summarize_router.get("/session/{session_id}")
async def get_session(session_id: str):
    try:
        session_data = await get_session_handler(session_id)
        if session_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or expired."
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=session_data.dict()
        )
    
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@summarize_router.get("/sse-stream/summarize")
async def stream_video_summary(
    session_id: str,
    model_resources=Depends(get_model_and_tokenizer),
    semaphore=Depends(get_request_semaphore),
):
    try:    
        model, tokenizer = model_resources
        session_data = await get_session_handler(session_id)
        if session_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or expired."
            )

        return EventSourceResponse(
            generate_video_summary_handler(
                videoId=session_data.videoId,
                sessionId=session_id,
                model=model,
                tokenizer=tokenizer,
                semaphore=semaphore,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        

    except torch.cuda.OutOfMemoryError:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Server resources overloaded. Please try again later.",
        )

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during processing: {str(e)}",
        )

@summarize_router.get("/sse-stream/trascript/{video_id}")
async def stream_transcript(video_id: str):
    try:
        return EventSourceResponse(
            generate_trascript_hander(video_id=video_id),
            media_type="text/event-stream",

            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )

    except torch.cuda.OutOfMemoryError:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Server resources overloaded. Please try again later.",
        )

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during summarization: {str(e)}",
        )

@summarize_router.get("/dummy-sse-stream")
async def dummy_stream():
    TEXT_BLOCK = """
[BEGIN-SUMMARY] 
[BEGIN-PARAGRAPH] රට දෙකකට බෙදෙනවා කියලා නෑනෙ අපි දැන් ලංකාවට ආපු සියලුම ජාත්‍යන්තර ගවේෂකයෝ කියපු කතාවක් තමයි මම ඊට පස්සේ හැද [END-PARAGRAPH] [BEGIN-METADATA] 
[BEGIN-DATA] [BEGIN-KEY] time_stamp_idx [END-KEY] [BEGIN-VALUE] 0 [END-VALUE] [END-DATA] 
[BEGIN-DATA] [BEGIN-KEY] from [END-KEY] [BEGIN-VALUE] 10 [END-VALUE] [END-DATA] 
[BEGIN-DATA] [BEGIN-KEY] to [END-KEY] [BEGIN-VALUE] 100 [END-VALUE] [END-DATA] 
[END-METADATA] 
[BEGIN-PARAGRAPH] උඩහමුල්ල ප්‍රශ්නය විසඳලා හල්මිල්ල හාට් එනවා මොකද්ද එකේ නම මට මතක නෑ එතන පල්ලෙහාට වෙනවා මොන කුමාරි ද කියලා තැනකට එන්න විදි [END-PARAGRAPH] 
[BEGIN-METADATA] 
[BEGIN-DATA] [BEGIN-KEY] time_stamp_idx [END-KEY] [BEGIN-VALUE] 1 [END-VALUE] [END-DATA] 
[BEGIN-DATA] [BEGIN-KEY] from [END-KEY] [BEGIN-VALUE] 100 [END-VALUE] [END-DATA] 
[BEGIN-DATA] [BEGIN-KEY] to [END-KEY] [BEGIN-VALUE] 120 [END-VALUE] [END-DATA] 
[END-METADATA] 
[BEGIN-PARAGRAPH] දැන් අපි eastern coast එකේ ටිකක් වගේම මීට පෙර මම ගත්තා පෝස්ට් එකක් නෑ කියලා.com එකට වෙන්නේ ස්වාභාවික හබ් එකකින් හෝ [END-PARAGRAPH] 
[BEGIN-METADATA]
[BEGIN-DATA] [BEGIN-KEY] time_stamp_idx [END-KEY] [BEGIN-VALUE] 2 [END-VALUE] [END-DATA] 
[BEGIN-DATA] [BEGIN-KEY] from [END-KEY] [BEGIN-VALUE] 120 [END-VALUE] [END-DATA] 
[BEGIN-DATA] [BEGIN-KEY] to [END-KEY] [BEGIN-VALUE] 200 [END-VALUE] [END-DATA] 
[END-METADATA] 
[BEGIN-PARAGRAPH] ඉන්දියා ඊශ්‍රායල් හිතන්නේ මේ බොරුවට රටද වෙනුවෙන් දෙකට බෙදෙනවා කියලා නිහාරා හැදුවා ඉන්පස්සෙ හෙල වෙන්නවත් අරගෙන එන්න බෑනේ අපි හිතන්න ඕන [END-PARAGRAPH] 
[BEGIN-METADATA]
[BEGIN-DATA] [BEGIN-KEY] time_stamp_idx [END-KEY] [BEGIN-VALUE] 3 [END-VALUE] [END-DATA] 
[BEGIN-DATA] [BEGIN-KEY] from [END-KEY] [BEGIN-VALUE] 200 [END-VALUE] [END-DATA] 
[BEGIN-DATA] [BEGIN-KEY] to [END-KEY] [BEGIN-VALUE] 300 [END-VALUE] [END-DATA]  
[BEGIN-DATA] [BEGIN-KEY] uid [END-KEY] [BEGIN-VALUE] abcd1234 [END-VALUE] [END-DATA] 
[BEGIN-DATA] [BEGIN-KEY] name [END-KEY] [BEGIN-VALUE] Janith Madarasinghe [END-VALUE] [END-DATA] 
[END-METADATA] 
[END-SUMMARY] 
[DONE]""".split()
    async def event_generator():
        for token in TEXT_BLOCK:
            if token == "[DONE]":
                break
            yield token
            await asyncio.sleep(0.1)
        

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@summarize_router.post("/without-category")
async def without_category(
    request: SummarizeRequest,
    user: User = Depends(verify_token),
    model_resources=Depends(get_model_and_tokenizer),
    semaphore=Depends(get_request_semaphore),
):
    model, tokenizer = model_resources
    if len(request.text) > 5000 or len(request.text) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text length must be between 100 and 5000 characters.",
        )
    
    try:
        summary = await generate_summary_without_category_handler(
            text=request.text,
            model=model,
            tokenizer=tokenizer
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "summary": postprocess_text(summary),
            }
        )
            
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during summarization: {str(e)}",
        )
    
@summarize_router.post("/with-category")
async def without_category(
    request: SummarizeWithCategoryRequest,
    user: User = Depends(verify_token),
    model_resources=Depends(get_with_category_model_and_tokenizer),
    semaphore=Depends(get_request_semaphore),
):
    model, tokenizer = model_resources
    if len(request.text) > 5000 or len(request.text) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text length must be between 100 and 5000 characters.",
        )
    
    try:
        summary = await generate_summary_with_category_handler(
            text=request.text,
            category=request.category,
            model=model,
            tokenizer=tokenizer
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "summary": postprocess_text(summary),
            }
        )
            
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during summarization: {str(e)}",
        )
    
@summarize_router.post("/with-predicted-category")
async def with_predicted_category(
    request: SummarizeRequest,
    user: User = Depends(verify_token),
    mt5_model_resources=Depends(get_with_category_model_and_tokenizer),
    bert_model_resources=Depends(get_sin_bert_model_and_tokenizer),
    semaphore=Depends(get_request_semaphore),
):
    mt5_model, mt5_tokenizer = mt5_model_resources
    bert_model, bert_tokenizer, bert_config = bert_model_resources
    
    if len(request.text) > 5000 or len(request.text) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text length must be between 100 and 5000 characters.",
        )
    
    try:
        async with semaphore:
            _, predicted_category = await predict_category_handler(
                    text=request.text,
                    model=bert_model,
                    tokenizer=bert_tokenizer,
                    config=bert_config,
                )
            
            summary = await generate_summary_with_category_handler(
                text=request.text,
                category=predicted_category['label'],
                model=mt5_model,
                tokenizer=mt5_tokenizer
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "category": predicted_category,
                    "summary": postprocess_text(summary),
                }
            )
            
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during summarization: {str(e)}",
        )