import aiohttp
import asyncio
import io
from typing import Optional
from m3u8 import M3U8
from pydub import AudioSegment
from pytube import YouTube
from collections.abc import AsyncGenerator
import yt_dlp

class YouTubeHandler:
    def __init__(self):
        self.chunk_size = 30
        self.max_retries = 3
        self.audio_bitrates = {}

    def is_live_video(self, video_id: str) -> Optional[bool]:
        """
        Checks if the provided video_id corresponds to a live stream.
        - Returns True if it is a live video, otherwise False.
        """
       
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {"quiet": True}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get("is_live")
             
        except Exception as exc:
            print(f"Error checking video status: {exc}")
            return None

    async def get_content(self, video_id: str, start_time = None) -> AsyncGenerator[AudioSegment, None]:
        """
        Entry point to process YouTube content.
        - For live streams, processes segments from the start to the join time.
        - For videos, processes chunks incrementally.
        """
        
        if self.is_live_video(video_id):
            return await self._process_live_stream(video_id, start_time) # type: ignore
        
        return await self._process_vod(video_id) # type: ignore

    async def _process_live_stream(self, video_id: str, join_time = None):
        """
        Processes a live stream by downloading and concatenating required segments.
        """
        async with aiohttp.ClientSession() as session:
            manifest_url = f"https://www.youtube.com/watch?v={video_id}"
            async with session.get(manifest_url) as resp:
                if resp.status != 200:
                    return None

                html = await resp.text()
                print(html)

                playlists = M3U8(await resp.text()).playlists
                print(playlists)
            
            audio_playlist = next(p for p in playlists if p.stream_info.audio == "audio")
            segments = self._calculate_required_segments(audio_playlist, join_time)

            return await self._download_segments(segments)

    def _calculate_required_segments(self, playlist, join_time):
        """
        Determines which segments of a live stream are required based on the join time.
        """
        segment_list = []
        current_time = 0
        for segment in playlist.segments:
            if current_time + segment.duration < join_time:
                segment_list.append(segment)
                current_time += segment.duration
        return segment_list

    async def _download_segments(self, segments):
        """
        Downloads and concatenates audio segments for live streams.
        """
        concatenated_audio = AudioSegment.empty()
        async with aiohttp.ClientSession() as session:
            for segment in segments:
                for attempt in range(self.max_retries):
                    try:
                        async with session.get(segment.uri) as response:
                            audio_data = await response.read()
                            chunk = AudioSegment.from_file(
                                io.BytesIO(audio_data),
                                format="mp4"
                            )
                            concatenated_audio += chunk
                            break
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            raise RuntimeError(f"Failed to download segment: {e}")
                        await asyncio.sleep(2 ** attempt)
        
        return concatenated_audio

    async def _process_vod(self, video_id: str) -> AsyncGenerator[AudioSegment, None]:
        """
        Processes a video (VOD) by downloading and processing it chunk by chunk.
        """
        yt = YouTube(f"https://youtu.be/{video_id}")
        stream = yt.streams.get_audio_only()

        bitrate_kbps = int(stream.abr.split("kbps")[0]) # type: ignore
        bitrate_bytes_per_second = bitrate_kbps * 1024 // 8
        chunk_size_bytes = bitrate_bytes_per_second * 30  # 30 seconds per chunk

        async with aiohttp.ClientSession() as session:
            async with session.get(stream.url) as response: # type: ignore
                buffer = b""
                while True:
                    data = await response.content.read(8192)
                    if not data:
                        break

                    buffer += data

                    if len(buffer) >= chunk_size_bytes:
                        audio_chunk, buffer = await self._split_audio_buffer(buffer)
                        yield audio_chunk

                if buffer:
                    audio_chunk = AudioSegment.from_file(io.BytesIO(buffer), format="webm")
                    yield audio_chunk

    async def _split_audio_buffer(self, buffer: bytes) -> tuple[AudioSegment, bytes]:
        """
        Splits an audio buffer into processable chunks.
        """
        audio = AudioSegment.from_file(io.BytesIO(buffer), format="webm")

        chunk_length_ms = 30 * 1000  # 30 seconds per chunk
        num_chunks = len(audio) // chunk_length_ms

        if num_chunks > 0:
            split_point_ms = num_chunks * chunk_length_ms
            first_chunk = audio[:split_point_ms]
            remaining_buffer_start_byte = split_point_ms * (
                audio.frame_rate // 1000
            ) * (audio.sample_width * audio.channels)

            return first_chunk, buffer[remaining_buffer_start_byte:]

        return None, buffer