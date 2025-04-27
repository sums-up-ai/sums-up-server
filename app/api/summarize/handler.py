import asyncio
import json
import os
import threading
from app.api.summarize.schemas import SessionData, SummarizeSessionRequest
from app.core.path_utils import get_project_path
from app.schemas.session import Status
from app.schemas.user import User
from app.services.firebase import firestore
from app.services.firebase.firestore import Firestore
import torch
from transformers import TextIteratorStreamer
from app.services.transcribe.sinhala_transcriber import SinhalaTranscriber
from app.services.youtube_handler.youtube_handler import YouTubeAudioProcessor
from app.core import settings
import logging
from pydub import AudioSegment
import os
from datetime import datetime, timedelta
from google.cloud.firestore_v1 import ArrayUnion


logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

summary_sessions = {}
store = Firestore(collection_name="ext_summarize")


TEXT_BLOCK = """Server-Sent Events enable real-time communication between servers and clients through a persistent HTTP connection. Unlike WebSockets, SSE is unidirectional - perfect for scenarios where the server needs to push updates without client interaction. [BREAK] This example demonstrates word-by-word streaming with FastAPI and React, simulating ChatGPT's typing effect. Each word appears sequentially, creating a natural reading experience. [BREAK]""".split()

async def create_session_handler(
    request: SummarizeSessionRequest,
    user: User
) -> str:
    request = {
        "uid": user.uid,
        "videoId": request.videoId,
        "title": request.title,
        "channelName": request.channelName,
        "thumbnailUrl": request.thumbnailUrl,
        "createdAt": datetime.now().isoformat(),
        "status": Status.sessionCreated,
    }

    sessionId = await store.create(request)
    request["sessionId"] = sessionId

    summary_sessions[sessionId] = {
        "data": request,
        "expiresAt": datetime.now() + timedelta(hours=1)
    }
    
    await store.update(sessionId, {"sessionId": sessionId})
    return sessionId

async def get_session_handler(sessionId: str) -> SessionData:
    if(sessionId not in summary_sessions):
        session_data = await store.get_by_id(sessionId)
        return SessionData.model_validate(session_data)

    else:
        session_data = summary_sessions[sessionId]
        if datetime.now() > session_data["expiresAt"]:
            del summary_sessions[sessionId]
            return None
        else:
            return SessionData.model_validate(session_data["data"])

async def is_session_available_handler(sessionId: str) -> bool:
    if(sessionId not in summary_sessions):
        session_data = await store.get_by_id(sessionId)
        return session_data is not None
    else:
        session_data = summary_sessions[sessionId]
        if datetime.now() > session_data["expiresAt"]:
            del summary_sessions[sessionId]
            return False
        else:
            return True


async def sse_stream_handler(session: SessionData):
    try:        
        await store.update(session.sessionId, {
            "summary": [],
            "status": Status.streaming,
        })
        
        token_generator = TEXT_BLOCK
        
        token_buffer = []

        for token in token_generator:

            await asyncio.sleep(0.1)

            if(token.strip() == "[BREAK]"):
                await store.update(session.sessionId, {
                    "summary": ArrayUnion([" ".join(token_buffer)]),
                    "updatedAt": datetime.now().isoformat()
                })
                token_buffer.clear()
                continue

            token_buffer.append(token) 
            yield token
        
        await store.update(session.sessionId, {
            "status": Status.completed,
            "updatedAt": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        await store.update(session.sessionId, {
            "status": Status.failed,
            "error": str(e)
        })
        yield f"Error in generation or Streaming: {str(e)}"


async def word_stream_handler(token: str):
    
    yield token
    await asyncio.sleep(0.1)

    for word in TEXT_BLOCK:
        await asyncio.sleep(0.1)
        yield word

async def generate_summary(text: str, model, tokenizer, min_length: int, max_length: int):
    
    processed_text = f"summarize: {text.strip()}"

    inputs = tokenizer(
        processed_text,
        return_tensors="pt",
        max_length=1024,
        truncation=True,
        padding=True,
        add_special_tokens=True
    ).to(settings.DEVICE)

    streamer = TextIteratorStreamer(
        tokenizer,
        skip_special_tokens=True,
        skip_prompt=True
    )

    def generate():
        with torch.inference_mode():
            model.generate(
                **inputs,
                max_length=max_length,
                min_length=min_length,
                num_beams=1,
                do_sample=False,
                streamer=streamer,
            )

    threading.Thread(target=generate, daemon=True).start()

    for token in streamer:
        yield token

async def generate_trascript(video_id: str, start_time=None):
    full_transcript = ""
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_script_dir, '..', '..', '..'))
    credentials_path = os.path.join(project_root, 'credentials', 'gcc.json')

    # credentials_path = get_project_path('credentials/gcc.json')

    audio_processor = YouTubeAudioProcessor()
    transcriber = SinhalaTranscriber(api_key=credentials_path)

    logger.info(f"Starting to process video: {video_id}")
    
    async for audio_chunk in audio_processor.process_content(video_id, start_time):

        transcript = await transcriber.transcribe_audio(audio_chunk)
        full_transcript += " " + transcript[0]['text'] # type: ignore
        yield transcript
        
        await asyncio.sleep(0.05)

    with open(f'transcript-{video_id}.txt', "w", encoding="utf-8") as f:
        f.write(full_transcript)


async def generate_transcript_and_summary(video_id: str, model, tokenizer, min_length: int, max_length: int, start_time=None):
    """
    Download audio from YouTube, transcribe it chunk by chunk,
    and generate summaries after processing multiple chunks.
    """
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_script_dir, '..', '..', '..'))
    credentials_path = os.path.join(project_root, 'credentials', 'gcc.json')

    # credentials_path = get_project_path('credentials/gcc.json')

    print(f"Credentials path: {credentials_path}")
    print(get_project_path('credentials/gcc.json'))


    audio_processor = YouTubeAudioProcessor()
    transcriber = SinhalaTranscriber(api_key=credentials_path)

    logger.info(f"Starting to process video: {video_id}")
    
    transcript_buffer = ""
    
    chunk_counter = 0
    
    chunks_before_summary = 3
    
    async for audio_chunk in audio_processor.process_content(video_id, start_time):
        current_transcript = await transcriber.transcribe_audio(audio_chunk)
        if(current_transcript is not None and len(current_transcript) > 0):
            transcript_buffer += " " + current_transcript[0]['text'] # type: ignore
            chunk_counter += 1
        
        if chunk_counter >= chunks_before_summary:
            chunk_counter = 0
            
            processed_text = f"summarize: {transcript_buffer.strip()}"
            
            inputs = tokenizer(
                processed_text,
                return_tensors="pt",
                max_length=1024,
                truncation=True,
                padding=True,
                add_special_tokens=True
            ).to(settings.DEVICE)
            
            streamer = TextIteratorStreamer(
                tokenizer,
                skip_special_tokens=True,
                skip_prompt=True
            )
            
            def generate():
                with torch.inference_mode():
                    model.generate(
                        **inputs,
                        max_length=max_length,
                        min_length=min_length,
                        num_beams=1,
                        do_sample=False,
                        streamer=streamer,
                    )
            
            threading.Thread(target=generate, daemon=True).start()
            
            for token in streamer:
                if token.strip():
                    yield {"type": "summary", "content": token}
                    await asyncio.sleep(0.01)
            
            transcript_buffer = ""
            yield {"type": "summary", "content": "[BREAK]"}
        
        await asyncio.sleep(0.05)
