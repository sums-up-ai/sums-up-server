import yt_dlp
import ffmpeg
import time
from queue import Queue
from threading import Thread

class YouTubeAudioExtractor:
    def __init__(self, video_id):
        self.video_id = video_id
        self.is_live = False
        self.stream_buffer = Queue()
        self._verify_stream_type()

    def _verify_stream_type(self):
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(f"https://youtu.be/{self.video_id}", download=False)
            self.is_live = info.get('is_live', False)

    def _process_uploaded_video(self):
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': f'%(id)s.%(ext)s'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([self.video_id])

    def _stream_callback(self, data):
        self.stream_buffer.put(data)

    def _live_stream_processor(self, start_time):
        ydl_opts = {
            'format': 'bestaudio/best',
            'live_from_start': True if start_time == 'beginning' else False,
            'buffer_size': 1024,
            'outtmpl': '-',
            'postprocessor_args': ['-ar', '16000', '-ac', '1'],
            'progress_hooks': [(lambda d: self._stream_callback(d['fragment']))],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtu.be/{self.video_id}"])

    def handle_live_stream(self, user_join_time):
        if self.is_live:
            stream_start = time.time() - user_join_time
            
            if stream_start > 300:
                print("Capturing from stream beginning")
                Thread(target=self._live_stream_processor, args=('beginning',)).start()
            else:
                print("Buffering initial 30 seconds...")
                time.sleep(30)
                Thread(target=self._live_stream_processor, args=('realtime',)).start()
                
            while True:
                if not self.stream_buffer.empty():
                    audio_chunk = self.stream_buffer.get()
                    yield audio_chunk

    def extract_audio(self):
        if self.is_live:
            return self.handle_live_stream(time.time())
        else:
            return self._process_uploaded_video()
