from google.cloud import speech
import io
import os
from typing import List, Dict
from pydub import AudioSegment

class SinhalaTranscriber:
    def __init__(self, api_key=None):
        # Set up Google Cloud credentials
        if api_key:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = api_key
        
        self.client = speech.SpeechClient()
        self.language_code = "si-LK"  # Sinhala language code
      
    async def transcribe_audio(self, audio_chunk: AudioSegment) -> List[Dict]:
        """Transcribe audio chunk"""
        # Convert to mono first
        mono_audio = audio_chunk.set_channels(1)
        
        # Convert audio to proper format for Google ASR
        with io.BytesIO() as audio_file:
            mono_audio.export(audio_file, format="wav")
            content = audio_file.getvalue()
        
        # Configure request
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=mono_audio.frame_rate,
            language_code=self.language_code,
            enable_automatic_punctuation=True,
            audio_channel_count=1,  # Explicitly specify mono
            enable_word_time_offsets=True,  # Get word-level timestamps
        )
        
        # Perform transcription
        response = self.client.recognize(config=config, audio=audio)
        
        # Process results
        transcribed_segments = []
        
        for result in response.results:
            for word_info in result.alternatives[0].words:
                word = word_info.word
                start_time = word_info.start_time.total_seconds()
                end_time = word_info.end_time.total_seconds()
                
                # Check if we should append to the last segment
                if (transcribed_segments and
                    start_time - transcribed_segments[-1]["end"] < 0.5):  # Small gap
                    
                    transcribed_segments[-1]["text"] += " " + word
                    transcribed_segments[-1]["end"] = end_time
                else:
                    # Create new segment
                    transcribed_segments.append({
                        "start": start_time,
                        "end": end_time,
                        "text": word
                    })
                        
        # Merge words into sentences
        merged_segments = self._merge_words_to_sentences(transcribed_segments)
        return merged_segments
    
    
    def _merge_words_to_sentences(self, word_segments: List[Dict]) -> List[Dict]:
        """Merge word-level segments into sentence-level segments"""
        if not word_segments:
            return []
            
        sentence_segments = []
        current = {
            "start": word_segments[0]["start"],
            "end": word_segments[0]["end"],
            "text": word_segments[0]["text"]
        }
        
        for segment in word_segments[1:]:
            # If no long pause, append
            if segment["start"] - current["end"] < 1.0:  # 1 second threshold
                current["text"] += " " + segment["text"]
                current["end"] = segment["end"]
            else:
                # Finish current sentence and start a new one
                sentence_segments.append(current)
                current = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"]
                }
                
        # Add the last segment
        sentence_segments.append(current)
        return sentence_segments