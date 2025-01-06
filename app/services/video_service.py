class VideoService:
    async def process_video(self, video_id: str) -> str:
        print(f"Processing video ID: {video_id}")
        return f"Your video ID: {video_id}"
