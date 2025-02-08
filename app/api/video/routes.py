from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from app.api.video.models import VideoRequest
from app.api.video.service import VideoService
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from app.services.web_socket_manager.web_sockect_manager import WSConnectionManager

import numpy as np
import torch
import asyncio
import subprocess
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

model_name = "Ransaka/whisper-tiny-sinhala-20k"
processor = WhisperProcessor.from_pretrained(model_name)
model = WhisperForConditionalGeneration.from_pretrained(model_name)
forced_decoder_ids = processor.get_decoder_prompt_ids(language="si", task="transcribe")

chunk_time = 16000 * 2 * 10

video_router = APIRouter(tags=["Video"])

websocket_manager = WSConnectionManager()

@video_router.post("/generate-url", summary="Generate YouTube URL")
async def generate_video_url(request: VideoRequest):
    try:
        return VideoService.generate_youtube_url(request.videoId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @video_router.websocket("/ws/transcribe/{user_id}/{video_id}")
# async def websocket_transcribe2(websocket: WebSocket, user_id:str, video_id: str):
#     process = None
#     try:
#         await websocket_manager.connect(user_id, websocket) 
#         print(f"WebSocket connected for video_id: {video_id}, user_id: {user_id}")

#         yt_url = f"https://www.youtube.com/watch?v={video_id}"
#         audio_url = await get_audio_stream_url(yt_url)
        
#         cmd = [
#             'ffmpeg', '-i', audio_url, '-loglevel', 'quiet',
#             '-f', 's16le', '-ac', '1', '-ar', '16000', '-'
#         ]
        
#         if sys.platform == 'win32':
#             process = subprocess.Popen(
#                 cmd,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.DEVNULL,
#                 creationflags=subprocess.CREATE_NO_WINDOW
#             )
            
#             while True:
#                 chunk = process.stdout.read(chunk_time)
#                 if not chunk:
#                     break
                    
#                 audio_array = np.frombuffer(chunk, np.int16).astype(np.float32) / 32768.0
#                 inputs = processor(
#                     audio_array, 
#                     sampling_rate=16000,
#                     return_tensors="pt"
#                 ).input_features.to(model.device)

#                 predicted_ids = model.generate(
#                     inputs,
#                     forced_decoder_ids=forced_decoder_ids,
#                     max_new_tokens=128,
#                     return_timestamps=False
#                 )
                
#                 text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
#                 await websocket.send_text(text)
#         else:

#             process = await asyncio.create_subprocess_exec(
#                 *cmd,
#                 stdout=asyncio.subprocess.PIPE,
#                 stderr=subprocess.DEVNULL
#             )
            
#             while True:
#                 chunk = await process.stdout.read(chunk_time)
#                 if not chunk:
#                     break
                    
#                 audio_array = np.frombuffer(chunk, np.int16).astype(np.float32) / 32768.0
#                 inputs = processor(
#                     audio_array, 
#                     sampling_rate=16000,
#                     return_tensors="pt"
#                 ).input_features.to(model.device)

#                 predicted_ids = model.generate(
#                     inputs,
#                     forced_decoder_ids=forced_decoder_ids,
#                     max_new_tokens=128,
#                     return_timestamps=False
#                 )
                
#                 text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
#                 await websocket.send_text(text)

#     except WebSocketDisconnect:
#         print(f"WebSocket disconnected for video_id: {video_id}")
#         await websocket.close()
#     except Exception as e:
#         print(f"Error: {str(e)}")
#         await websocket.send_text(f"Error: {str(e)}")
#         await websocket.close()
#     finally:
#         if process:
#             if sys.platform == 'win32':
#                 process.terminate()
#             else:
#                 process.terminate()
#                 await process.wait()

async def get_audio_stream_url(yt_url: str):
    if sys.platform == 'win32':
        process = subprocess.run(
            ['yt-dlp', '-f', 'bestaudio/best', '--get-url', yt_url],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return process.stdout.strip()
    else:
        process = await asyncio.create_subprocess_exec(
            'yt-dlp', '-f', 'bestaudio/best', '--get-url', yt_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        stdout, _ = await process.communicate()
        return stdout.decode().strip()

@video_router.websocket('/ws/transcribe/{user_id}/{video_id}')
async def websocket_transcribe(websocket: WebSocket, user_id:str, video_id: str):
    try:
        await websocket_manager.connect(user_id, websocket) 
        print(f"WebSocket connected for user_id: {user_id}")
        while True:
            await websocket_manager.send_personal_message(f"WebSocket with video_id: {video_id}", user_id)
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        websocket_manager.disconnect(user_id)
        print(f"User {user_id} disconnected.")
