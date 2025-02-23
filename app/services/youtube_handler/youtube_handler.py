import subprocess
import tempfile
import os
import time
import aiohttp
import asyncio
import logging
from typing import Optional, AsyncGenerator
from m3u8 import M3U8
from pydub import AudioSegment
import yt_dlp

logger = logging.getLogger(__name__)

class YouTubeAudioProcessor:
    def __init__(self):
        self.chunk_duration = 30  # Seconds
        self.max_retries = 5
        self.base_backoff = 1.5
        self.live_refresh_interval = 10  # Manifest refresh interval for live streams

    async def process_content(self, video_id: str, start_time = None) -> AsyncGenerator[AudioSegment, None]:
        """Main entry point for both live and VOD content processing"""
        
        is_live = await self._check_live_status(video_id)
        
        if is_live:
            async for chunk in self._handle_live_stream(video_id, start_time):
                yield chunk
        else:
            async for chunk in self._handle_vod(video_id):
                yield chunk

    async def _check_live_status(self, video_id: str) -> bool:
        """Improved live status detection with better error handling"""
        
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "skip_download": True,
        }

        for attempt in range(self.max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://youtu.be/{video_id}", download=False)
                    return info.get("is_live", False)
           
            except yt_dlp.DownloadError as e:
                logger.warning(f"Live check attempt {attempt+1} failed: {str(e)}")
                await asyncio.sleep(self.base_backoff ** attempt)
        
        raise RuntimeError(f"Failed to determine live status after {self.max_retries} attempts")

    async def _handle_live_stream(self, video_id: str, join_time) -> AsyncGenerator[AudioSegment, None]:
        """Enhanced live stream handling with dynamic manifest updates"""
        
        last_segment = None
        downloaded_segments = set()

        while True:
            try:
                manifest_url = await self._get_live_manifest(video_id)
                async with aiohttp.ClientSession() as session:
                    async with session.get(manifest_url) as response:
                        playlist = M3U8(await response.text())
                
                audio_playlist = next(p for p in playlist.playlists if p.stream_info.audio)
                segments = self._filter_segments(audio_playlist, join_time, last_segment)
                
                async for chunk in self._process_segments(segments, downloaded_segments):
                    yield chunk
                    last_segment = chunk

                await asyncio.sleep(self.live_refresh_interval)

            except Exception as e:
                logger.error(f"Live stream error: {str(e)}")
                await self._handle_retry("live_stream")

    async def _get_live_manifest(self, video_id: str) -> str:
        """Proper manifest URL extraction using yt-dlp"""
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "format": "bestaudio",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://youtu.be/{video_id}", download=False)
            if not info.get('is_live'):
                raise ValueError("Video is not live")
            
            for fmt in info.get('formats', []):
                if fmt.get('protocol') == 'm3u8' and fmt.get('audio_ext') != 'none':
                    return fmt['url']
            
            raise RuntimeError("No valid HLS audio manifest found")

    def _filter_segments(self, playlist, join_time, last_segment) -> list:
        """Time-aware segment filtering with expiration check"""
        valid_segments = []
        now = time.time()
        
        for segment in playlist.segments:
            if (segment.program_date_time.timestamp() > join_time and 
                segment.program_date_time.timestamp() < now - playlist.target_duration):
                valid_segments.append(segment)
        
        return valid_segments

    async def _process_segments(self, segments, downloaded_segments) -> AsyncGenerator[AudioSegment, None]:
        """Segment processing with expiration awareness"""
        async with aiohttp.ClientSession() as session:
            for segment in segments:
                if segment.uri in downloaded_segments:
                    continue
                
                for attempt in range(self.max_retries):
                    try:
                        async with session.get(segment.uri) as response:
                            audio_data = await response.read()
                            chunk = await self._convert_to_pcm(audio_data)
                            downloaded_segments.add(segment.uri)
                            yield chunk
                            break
                    except Exception as e:
                        logger.warning(f"Segment {segment.uri} failed (attempt {attempt+1}): {str(e)}")
                        await asyncio.sleep(self.base_backoff ** attempt)

    async def _handle_vod(self, video_id: str) -> AsyncGenerator[AudioSegment, None]:
        """Improved VOD handling with frame-accurate splitting"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "quiet": True,
                "format": "bestaudio/best",
                "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://youtu.be/{video_id}", download=True)
                audio_file = ydl.prepare_filename(info)

            ffmpeg_cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-i", audio_file,
                "-f", "segment",
                "-segment_time", str(self.chunk_duration),
                "-c:a", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                "-map", "0:a",
                "-segment_format", "wav",
                "chunk-%03d.wav"
            ]

            subprocess.run(ffmpeg_cmd, check=True, cwd=tmpdir)

            chunk_num = 0
            while True:
                chunk_path = os.path.join(tmpdir, f"chunk-{chunk_num:03d}.wav")
                if not os.path.exists(chunk_path):
                    break
                
                with open(chunk_path, "rb") as f:
                    audio = AudioSegment.from_wav(f)
                    yield audio
                
                chunk_num += 1

    async def _convert_to_pcm(self, audio_data: bytes) -> AudioSegment:
        """Convert arbitrary audio formats to standardized PCM"""
        with tempfile.NamedTemporaryFile() as temp_in:
            temp_in.write(audio_data)
            temp_in.flush()
            
            with tempfile.NamedTemporaryFile(suffix=".wav") as temp_out:
                subprocess.run([
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel", "error",
                    "-i", temp_in.name,
                    "-ar", "44100",
                    "-ac", "2",
                    "-c:a", "pcm_s16le",
                    "-y", temp_out.name
                ], check=True)
                
                return AudioSegment.from_wav(temp_out.name)

    async def _handle_retry(self, context: str):
        """Unified retry handler with exponential backoff"""
        logger.warning(f"Retrying {context}...")
        await asyncio.sleep(self.base_backoff)



if __name__ == "__main__":
    async def test_check_live_status():
        processor = YouTubeAudioProcessor()
        print(await processor._check_live_status("9628jILczok")) # VOD
        print(await processor._check_live_status("eFC-sPbI41I")) # Live

    # async def test_():
    #     processor = YouTubeAudioProcessor()
    #     async for chunk in processor.process_content("9628jILczok"):
    #         print(f"Received {len(chunk)}ms audio chunk")
    #         print("Processing...")
    #         await asyncio.sleep(1)
    #         print("Done")

    asyncio.run(test_check_live_status())

