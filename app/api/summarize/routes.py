import asyncio
from app.api.summarize.handler import create_session_handler, generate_summary_with_category_handler, generate_summary_without_category_handler, get_session_handler, get_video_summary_handler
from app.api.summarize.schemas import SummarizeSessionRequest, SummarizeWithCategoryRequest
from app.core.firebase import verify_token
from app.schemas.user import User
from app.services.firebase.firestore import Firestore
from app.services.model_dependencies.mt5 import get_with_category_model_and_tokenizer
from app.services.post_processing.zero_with_char import postprocess_text
import torch
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from app.api.summarize import SummarizeRequest, generate_summary, generate_trascript
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

@summarize_router.get("/sse-stream")
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
            get_video_summary_handler(
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

@summarize_router.post("/sse-stream/summarize")
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

            def token_stream(generator):
                for token in generator:
                    if token == "[DONE]":
                        break
                    yield token

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

@summarize_router.get("/sse-stream/trascript/{video_id}")
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

@summarize_router.get("/dummy-sse-stream")
async def dummy_stream():
    TEXT_BLOCK = """[BEGIN-SUMMARY] [BEGIN-PARAGRAPH] දිවයින පුරා ඇද හැළුණු අධික වර්ශාපතනය හමුවේ වාරිමාර්ග දෙපාර්තමේන්තුවට අයත් ප්‍රධාන ජලාශ අතුරින් ජලාශ 24ක් මේ වන විට වාන් දමමින් පවතින බව වාරිමාර්ග දෙපාර්තමේන්තුව පවසයි. [END-PARAGRAPH] [BEGIN-PARAGRAPH] මෙම වාන් දමන ප්‍රධාන ජලාශ අතරින් අම්පාර දිස්ත්‍රික්කයේ ජලාශ 6ක්, හම්බන්තොට දිස්ත්‍රික්කයේ ජලාශ 6ක්, අනුරාධපුර දිස්ත්‍රික්කයේ ප්‍රධාන ජලාශ 4ක්, බදුල්ල, කුරුණෑගල, මොනරාගල, ත්‍රිකුණාමලය දිස්ත්‍රික්කවල ඇති ජලාශවලින් ජලාශ 2 බැගින්ද මුළු ජලාශ 24ක් පවතින බවද එම දෙපාර්තමේන්තුව සඳහන් කළේය. [END-PARAGRAPH] [BEGIN-PARAGRAPH] මෙම ප්‍රධාන ජලාශයන්ට අමතරව මධ්‍යම පරිමාණයේ ජලාශ 16කට අධික ප්‍රමාණයක්ද වාන් දමමින් පවතින බව පැවසූ වාරිමාර්ග දෙපාර්තමේන්තුව සඳහන් කළේ දෙපාර්තමේන්තුව සතුව පවතින ප්‍රධාන සහ මධ්‍යම ප්‍රමාණයේ ජලාශවල ගබඩා කරගත හැකි මුළු ජල ධාරිතාවෙන් 91%කට වැඩි ප්‍රමාණයක් මේ වන විට ගබඩා කර ගත හැකි වී ඇති බවය. [END-PARAGRAPH] [END-SUMMARY] [DONE]""".split()
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