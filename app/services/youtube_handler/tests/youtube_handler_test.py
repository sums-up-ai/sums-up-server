import pytest
from ..youtube_handler import YouTubeHandler

class TestYouTubeHandler:
    @pytest.mark.parametrize("video_id, is_live, expected", [
        # Live video
        ("eFC-sPbI41I", True, True),
        ("hqCuPXekVaQ", True, True),
        
        # VOD
        ("9628jILczok", False, False),
        ("92XfSaT-ZVw", False, False),
        
        # Invalid video ID
        ("", False, None),
        ("bad_id!", False, None)
    ])
    
    def test_is_live_video(self, video_id, expected):
        handler = YouTubeHandler()
        result = handler.is_live_video(video_id)
        assert result == expected
