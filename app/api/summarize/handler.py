import asyncio
import os
import threading
from app.api.summarize.schemas import SessionData, SummarizeSessionRequest
from app.core.path_utils import get_project_path
from app.schemas.session import Status
from app.schemas.user import User
from app.services.firebase.firestore import Firestore
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


TEXT_BLOCK = """[START-SUMMARY] දිවයින පුරා ඇද හැළුණු අධික වර්ශාපතනය හමුවේ වාරිමාර්ග දෙපාර්තමේන්තුවට අයත් ප්‍රධාන ජලාශ අතුරින් ජලාශ 24ක් මේ වන විට වාන් දමමින් පවතින බව වාරිමාර්ග දෙපාර්තමේන්තුව පවසයි. [BREAK]

මෙම වාන් දමන ප්‍රධාන ජලාශ අතරින් අම්පාර දිස්ත්‍රික්කයේ ජලාශ 6ක්, හම්බන්තොට දිස්ත්‍රික්කයේ ජලාශ 6ක්, අනුරාධපුර දිස්ත්‍රික්කයේ ප්‍රධාන ජලාශ 4ක්, බදුල්ල, කුරුණෑගල, මොනරාගල, ත්‍රිකුණාමලය දිස්ත්‍රික්කවල ඇති ජලාශවලින් ජලාශ 2 බැගින්ද මුළු ජලාශ 24ක් පවතින බවද එම දෙපාර්තමේන්තුව සඳහන් කළේය. [BREAK]

මෙම ප්‍රධාන ජලාශයන්ට අමතරව මධ්‍යම පරිමාණයේ ජලාශ 16කට අධික ප්‍රමාණයක්ද වාන් දමමින් පවතින බව පැවසූ වාරිමාර්ග දෙපාර්තමේන්තුව සඳහන් කළේ දෙපාර්තමේන්තුව සතුව පවතින ප්‍රධාන සහ මධ්‍යම ප්‍රමාණයේ ජලාශවල ගබඩා කරගත හැකි මුළු ජල ධාරිතාවෙන් 91%කට වැඩි ප්‍රමාණයක් මේ වන විට ගබඩා කර ගත හැකි වී ඇති බවය. [END-SUMMARY] [DONE]""".split()

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

async def get_video_summary_handler(
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
    maxNumOfChunks = 4

    audioProcessor = YouTubeAudioProcessor()
    transcriber = SinhalaTranscriber(api_key=credentials_path)
    
    logger.info(f"Starting to process video: {videoId}")
    
    async with semaphore:
        yield "[START-SUMMARY]"
        
        async for audio_chunk in audioProcessor.process_content(videoId, None):
            transcript_chunk = await transcriber.transcribe_audio(audio_chunk)
            transcripts.append(transcript_chunk['text'])
            chunkCounter += 1

            if chunkCounter >= maxNumOfChunks:
                chunkCounter = 0
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
                            max_length=50,
                            min_length=150,
                            num_beams=1,
                            do_sample=False,
                            streamer=streamer,
                        )
                
                threading.Thread(target=generate, daemon=True).start()

                yield "[START-PARAGRAPH]"
                
                for token in streamer:
                    if token.strip():
                        summaryParagraphs.append(token)
                        yield token
                        await asyncio.sleep(0.01)
                            
                await store.update(sessionId, {
                    "summary": ArrayUnion([" ".join(summaryParagraphs)]),
                    "updatedAt": datetime.now().isoformat()
                })
                
                transcripts.clear()
                summaryParagraphs.clear()
                
                yield "[END-PARAGRAPH]"

            await asyncio.sleep(0.05)
        
        yield "[END-SUMMARY]"

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