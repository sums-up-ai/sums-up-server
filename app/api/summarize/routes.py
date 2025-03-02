import asyncio
import torch
from fastapi import APIRouter, HTTPException, Depends, status
from sse_starlette.sse import EventSourceResponse
from app.api.summarize import SummarizeRequest, generate_summary, generate_trascript
from app.services.models import get_model_and_tokenizer, get_request_semaphore
import logging
from pydub import AudioSegment
from typing import Dict, List
import os



logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


summarize_router = APIRouter(tags=['summarize'])

async def token_stream(generator):
    async for token in generator:
        if token.strip():
            yield token
            await asyncio.sleep(0.05)
    yield "[DONE]"


@summarize_router.post("/summarize/stream")
async def stream_summary(
    request: SummarizeRequest,
    model_resources=Depends(get_model_and_tokenizer),
    semaphore=Depends(get_request_semaphore),
):

    model, tokenizer = model_resources

    if len(request.text) > 5000 or len(request.text) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text length must be between 100 and 5000 characters.",
        )

    async with semaphore:
        try:
            generator = generate_summary(
                text=request.text,
                model=model,
                tokenizer=tokenizer,
                min_length=request.min_length,
                max_length=request.max_length,
            )

            return EventSourceResponse(
                token_stream(generator),
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


@summarize_router.post("/trascript/stream/{video_id}")
async def stream_transcript(video_id: str):

    try:
        return EventSourceResponse(
            generate_trascript(video_id=video_id),
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