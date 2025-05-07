from google.cloud import speech
import io
import os
from typing import List, Dict
from pydub import AudioSegment

class SinhalaTranscriber:
    def __init__(self, api_key=None):
        if api_key:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = api_key
        
        self.client = speech.SpeechClient()
        self.language_code = "si-LK"
      
    async def transcribe_audio(self, audio_chunk: AudioSegment) -> Dict:
        mono_audio = audio_chunk.set_channels(1)
        
        with io.BytesIO() as audio_file:
            mono_audio.export(audio_file, format="wav")
            content = audio_file.getvalue()
        
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=mono_audio.frame_rate,
            language_code=self.language_code,
            enable_automatic_punctuation=True,
            audio_channel_count=1,
            enable_word_time_offsets=True,
        )
        
        response = self.client.recognize(config=config, audio=audio)
        
        transcribed_segments = []
        
        for result in response.results:
            for word_info in result.alternatives[0].words:
                word = word_info.word
                start_time = word_info.start_time.total_seconds()
                end_time = word_info.end_time.total_seconds()
                
                if (transcribed_segments and
                    start_time - transcribed_segments[-1]["end"] < 0.5):
                    
                    transcribed_segments[-1]["text"] += " " + word
                    transcribed_segments[-1]["end"] = end_time
                else:
                    transcribed_segments.append({
                        "start": start_time,
                        "end": end_time,
                        "text": word
                    })
                        
        merged_segments = self._merge_words_to_sentences(transcribed_segments)
        if not merged_segments:
            return {"start": 0, "end": 0, "text": ""}
        else:
            return merged_segments[0]
    
    
    def _merge_words_to_sentences(self, word_segments: List[Dict]) -> List[Dict]:
        if not word_segments:
            return []
            
        sentence_segments = []
        current = {
            "start": word_segments[0]["start"],
            "end": word_segments[0]["end"],
            "text": word_segments[0]["text"]
        }
        
        for segment in word_segments[1:]:
            if segment["start"] - current["end"] < 1.0:
                current["text"] += " " + segment["text"]
                current["end"] = segment["end"]
            else:
                sentence_segments.append(current)
                current = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"]
                }
                
        sentence_segments.append(current)
        return sentence_segments