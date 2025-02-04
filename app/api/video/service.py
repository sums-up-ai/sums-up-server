from datetime import datetime
from app.services.video_processing.audio_extractor import YouTubeAudioExtractor

class VideoService:
    @staticmethod
    def generate_youtube_url(video_id: str) -> dict:

        extractor = YouTubeAudioExtractor(video_id)
        extractor.extract_audio()

        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "data": {
                "youtube_url": f"https://www.youtube.com/watch?v={video_id}"
            }
        }