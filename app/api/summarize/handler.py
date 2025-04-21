import asyncio
import os
import threading
from app.core.path_utils import get_project_path
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


logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

summary_sessions = {}
store = Firestore(collection_name="ext_summarize")

async def create_session_handler(request) -> str:
    summary_session_data = {
        "video_id": request.videoId,
        "title": request.title,
        "channel_name": request.channelName,
        "thumbnail": request.thumbnailUrl,
        "created_at": datetime.now().isoformat(),
        "status": "processing",
        "progress": 0.0
    }

    session_id = await store.create(summary_session_data)
        
    summary_sessions[session_id] = {
        "data": summary_session_data,
        "expires_at": datetime.now() + timedelta(hours=1)
    }
    
    await store.update(session_id, {"session_id": session_id})
    return session_id

async def get_session_handler(session_id: str):
    if(session_id not in summary_sessions):
        return await store.get_by_id(session_id)
    else:
        session_data = summary_sessions[session_id]
        if datetime.now() > session_data["expires_at"]:
            del summary_sessions[session_id]
            return None
        else:
            return session_data["data"]



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
    
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_script_dir, '..', '..', '..'))
    credentials_path = os.path.join(project_root, 'credentials', 'gcc.json')

    # credentials_path = get_project_path('credentials/gcc.json')

    audio_processor = YouTubeAudioProcessor()
    transcriber = SinhalaTranscriber(api_key=credentials_path)

    logger.info(f"Starting to process video: {video_id}")
    
    async for audio_chunk in audio_processor.process_content(video_id, start_time):

        transcript = await transcriber.transcribe_audio(audio_chunk)
        yield transcript
        
        await asyncio.sleep(0.05)


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
