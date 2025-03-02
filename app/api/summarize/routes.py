import asyncio
import torch
from fastapi import APIRouter, HTTPException, Depends, status
from app.services.transcribe.sinhala_transcriber import SinhalaTranscriber
from app.services.youtube_handler.youtube_handler import YouTubeAudioProcessor
from sse_starlette.sse import EventSourceResponse
from app.api.summarize import SummarizeRequest, generate_summary
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

        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_script_dir, '..', '..', '..'))
        credentials_path = os.path.join(project_root, 'credentials', 'sums-up-server-452408-24ff39a211a6.json')

        audio_processor = YouTubeAudioProcessor()
        transcriber = SinhalaTranscriber(api_key=credentials_path)
        chunk_count = 0

        async def process_video(video_id: str, start_time=None, chunk_count=0):
            """Process a YouTube video or livestream and return transcripts in real-time"""
            logger.info(f"Starting to process video: {video_id}")
            
            async for audio_chunk in audio_processor.process_content(video_id, start_time):
                # Process each chunk for transcription
                transcript = await _process_chunk(audio_chunk, chunk_count)
                print(f"\nChunk {chunk_count} transcript:")
                yield transcript
                chunk_count += 1
        
        async def _process_chunk(audio_chunk: AudioSegment, chunk_id: int) -> List[Dict]:
            """Process a single audio chunk and return the transcript"""
            logger.info(f"Processing chunk {chunk_id}: Transcribing audio...")
            transcript = await transcriber.transcribe_audio(audio_chunk)
            return transcript

        return EventSourceResponse(
            process_video(video_id=video_id, chunk_count=chunk_count),
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