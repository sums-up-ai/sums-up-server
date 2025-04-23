import asyncio
from app.api.summarize.handler import create_session_handler, get_session_handler, sse_stream_handler
from app.api.summarize.schemas import SummarizeSessionRequest
from app.core.firebase import verify_token
from app.schemas.user import User
import torch
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from app.api.summarize import SummarizeRequest, generate_summary, generate_trascript, generate_transcript_and_summary
from app.services.models import get_model_and_tokenizer, get_request_semaphore
import logging
from pydub import AudioSegment
from typing import Dict, List
import os


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
        
@summarize_router.get("/sse-stream")
async def sse_stream(session_id: str):
    
    try:
        session_data = await get_session_handler(session_id)
        if session_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or expired."
            )
    
        return EventSourceResponse(
            sse_stream_handler(session_data),
        )
    
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


# @summarize_router.post("/transcribe-and-summarize/stream/{video_id}")
# async def stream_transcript_and_summary(
#     video_id: str,
#     min_length: int = 50,
#     max_length: int = 150,
#     start_time = None,
#     model_resources=Depends(get_model_and_tokenizer),
#     semaphore=Depends(get_request_semaphore),
# ):
#     model, tokenizer = model_resources

#     async with semaphore:
#         try:
#             generator = generate_transcript_and_summary(
#                 video_id=video_id,
#                 model=model,
#                 tokenizer=tokenizer,
#                 min_length=min_length,
#                 max_length=max_length,
#                 start_time=start_time
#             )

#             async def format_stream():
#                 async for event in generator:
#                     event_type = event["type"]
#                     content = event["content"]
#                     yield f"event: {event_type}\ndata: {content}\n\n"
#                 yield f"event: done\ndata: [DONE]\n\n"

#             return EventSourceResponse(
#                 format_stream(),
#                 media_type="text/event-stream",
#                 headers={
#                     "Cache-Control": "no-cache",
#                     "Connection": "keep-alive",
#                     "Access-Control-Allow-Origin": "*",
#                 }
#             )
        

#         except torch.cuda.OutOfMemoryError:
#             raise HTTPException(
#                 status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
#                 detail="Server resources overloaded. Please try again later.",
#             )

#         except Exception as e:
#             print(e)
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=f"An error occurred during processing: {str(e)}",
#             )


# @summarize_router.post("/summarize/stream")
# async def stream_summary(
#     request: SummarizeRequest,
#     model_resources=Depends(get_model_and_tokenizer),
#     semaphore=Depends(get_request_semaphore),
# ):

#     model, tokenizer = model_resources

#     if len(request.text) > 5000 or len(request.text) < 100:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Text length must be between 100 and 5000 characters.",
#         )

#     async with semaphore:
#         try:
#             generator = generate_summary(
#                 text=request.text,
#                 model=model,
#                 tokenizer=tokenizer,
#                 min_length=request.min_length,
#                 max_length=request.max_length,
#             )

#             return EventSourceResponse(
#                 token_stream(generator),
#                 media_type="text/event-stream",

#                 headers={
#                     "Cache-Control": "no-cache",
#                     "Connection": "keep-alive",
#                     "Access-Control-Allow-Origin": "*",
#                 }
#             )

#         except torch.cuda.OutOfMemoryError:
#             raise HTTPException(
#                 status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
#                 detail="Server resources overloaded. Please try again later.",
#             )

#         except Exception as e:
#             print(e)
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail=f"An error occurred during summarization: {str(e)}",
#             )


# @summarize_router.post("/trascript/stream/{video_id}")
# async def stream_transcript(video_id: str):

#     try:
#         return EventSourceResponse(
#             generate_trascript(video_id=video_id),
#             media_type="text/event-stream",

#             headers={
#                 "Cache-Control": "no-cache",
#                 "Connection": "keep-alive",
#                 "Access-Control-Allow-Origin": "*",
#             }
#         )

#     except torch.cuda.OutOfMemoryError:
#         raise HTTPException(
#             status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
#             detail="Server resources overloaded. Please try again later.",
#         )

#     except Exception as e:
#         print(e)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"An error occurred during summarization: {str(e)}",
#         )
    
