import asyncio
import os
import threading
from app.api.summarize.schemas import SessionData, SummarizeSessionRequest
from app.schemas.session import Status
from app.schemas.user import User
from app.services.firebase.firestore import Firestore
from app.services.post_processing.check_token import SINHALA_ZWJ, needs_zwj
import app.specification.tags as SSE_TAGS
import torch
from transformers import TextIteratorStreamer
from app.services.transcribe.sinhala_transcriber import SinhalaTranscriber
from app.services.youtube_handler.youtube_handler import YouTubeAudioProcessor
from app.core import settings
import logging
import os
from datetime import datetime, timedelta
from google.cloud.firestore_v1 import ArrayUnion

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

summary_sessions = {}
store = Firestore(collection_name="ext_summarize")

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


async def generate_video_summary_handler(
    videoId: str,
    sessionId: str,
    model,
    tokenizer, 
    semaphore
):
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_script_dir, '..', '..', '..'))
    credentials_path = os.path.join(project_root, 'credentials', 'gcc.json')

    transcripts = []
    summaryParagraphs = []
    chunkCounter = 0
    fromTime = 0
    maxNumOfChunks = 10

    audioProcessor = YouTubeAudioProcessor()
    transcriber = SinhalaTranscriber(api_key=credentials_path)
    
    logger.info(f"Starting to process video: {videoId}")
    
    async with semaphore:
        
        yield SSE_TAGS.BEGIN_SUMMARY
        
        async for audio_chunk in audioProcessor.process_content(videoId, None):
            transcript_chunk = await transcriber.transcribe_audio(audio_chunk)
            transcripts.append(transcript_chunk['text'])
            chunkCounter += 1

            if chunkCounter >= maxNumOfChunks:
                inputText = " ".join(transcripts).strip()
                
                inputs = tokenizer(
                    f"summarize: {inputText}",
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
                            max_length=500,
                            min_length=50,
                            num_beams=1,
                            do_sample=False,
                            streamer=streamer,
                        )
                
                threading.Thread(target=generate, daemon=True).start()

                yield SSE_TAGS.BEGIN_PARAGRAPH
                
                prev_token = None
                for token in streamer:
                    token = token.strip()
                    if not token:
                        continue
                    if prev_token is not None:
                        if needs_zwj(prev_token, token):
                            combined = prev_token + SINHALA_ZWJ + token
                            summaryParagraphs.append(combined)
                            yield combined
                            prev_token = None
                        else:
                            summaryParagraphs.append(prev_token)
                            yield prev_token
                            prev_token = token
                    else:
                        prev_token = token
                    await asyncio.sleep(0.1)

                if prev_token:
                    summaryParagraphs.append(prev_token)
                    yield prev_token
                            
                await store.update(sessionId, {
                    "summary": ArrayUnion([" ".join(summaryParagraphs)]),
                    "updatedAt": datetime.now().isoformat()
                })
             
                yield SSE_TAGS.END_PARAGRAPH
                
                yield SSE_TAGS.BEGIN_METADATA
                for data in SSE_TAGS.YIELD_DATA("from", fromTime * 30):
                    yield data
                yield SSE_TAGS.END_METADATA
                
                fromTime += chunkCounter
                chunkCounter = 0
                transcripts.clear()
                summaryParagraphs.clear()

            await asyncio.sleep(0.05)
        
        if transcripts:
            inputText = " ".join(transcripts).strip()
            inputs = tokenizer(
                f"summarize: {inputText}",
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
                        max_length=500,
                        min_length=50,
                        num_beams=1,
                        do_sample=False,
                        streamer=streamer,
                    )

            threading.Thread(target=generate, daemon=True).start()

            yield SSE_TAGS.BEGIN_PARAGRAPH

            prev_token = None
            for token in streamer:
                token = token.strip()
                if not token:
                    continue
                if prev_token is not None:
                    if needs_zwj(prev_token, token):
                        combined = prev_token + SINHALA_ZWJ + token
                        summaryParagraphs.append(combined)
                        yield combined
                        prev_token = None
                    else:
                        summaryParagraphs.append(prev_token)
                        yield prev_token
                        prev_token = token
                else:
                    prev_token = token
                await asyncio.sleep(0.01)

            if prev_token:
                summaryParagraphs.append(prev_token)
                yield prev_token

            await store.update(sessionId, {
                "summary": ArrayUnion([" ".join(summaryParagraphs)]),
                "updatedAt": datetime.now().isoformat()
            })

            yield SSE_TAGS.END_PARAGRAPH

            yield SSE_TAGS.BEGIN_METADATA
            for data in SSE_TAGS.YIELD_DATA("from", fromTime * 30):
                yield data
            yield SSE_TAGS.END_METADATA
            
        yield SSE_TAGS.END_SUMMARY
        yield '[DONE] \n\n'

async def generate_trascript_hander(video_id: str, start_time=None):
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_script_dir, '..', '..', '..'))
    credentials_path = os.path.join(project_root, 'credentials', 'gcc.json')

    # credentials_path = get_project_path('credentials/gcc.json')

    audio_processor = YouTubeAudioProcessor()
    transcriber = SinhalaTranscriber(api_key=credentials_path)

    logger.info(f"Starting to process video: {video_id}")
    
    async for audio_chunk in audio_processor.process_content(video_id, start_time):
        transcript = await transcriber.transcribe_audio(audio_chunk)
        if isinstance(transcript, list) and len(transcript) > 0:
            yield transcript[0]['text']
        else:
            yield transcript['text']
        
        await asyncio.sleep(0.05)

async def generate_summary_without_category_handler(
    text: str,
    model,
    tokenizer,
):
    inputs = tokenizer("summarize: " + text, return_tensors="pt", max_length=1024, truncation=True)
    summary_ids = model.generate(inputs["input_ids"], max_length=256, min_length=30, length_penalty=2.0, num_beams=4)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True) 
    return summary     

async def generate_summary_with_category_handler(
    text: str,
    category: str,
    model,
    tokenizer,
):
    inputs = tokenizer("summarize: category: " + category + " text: "+ text, return_tensors="pt", max_length=1024, truncation=True)
    summary_ids = model.generate(inputs["input_ids"], max_length=256, min_length=30, length_penalty=2.0, num_beams=4)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True) 
    return summary     