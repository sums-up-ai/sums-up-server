import torch
from pyannote.audio import Pipeline
from pyannote.core import Segment
import numpy as np
from pydub import AudioSegment
from typing import Dict, List, Tuple
from app.core.config import settings
import os
import tempfile

class SpeakerDiarizer:
    def __init__(self, access_token=None):
        # Load the pretrained model
        self.access_token = access_token or os.environ.get("PYANNOTE_AUTH_TOKEN")
        self.pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization", 
            use_auth_token=self.access_token
        )
        self.device = torch.device(settings.DEVICE)
        self.pipeline.to(self.device)
        
        # Speaker memory for consistent identification across chunks
        self.speaker_embeddings = {}
        self.chunk_count = 0
        self.is_initialized = False

    async def process_initial_chunks(self, audio_chunks: List[AudioSegment]) -> Dict:
        """Process initial chunks to identify speakers"""
        # Combine initial chunks for better speaker identification
        combined_audio = audio_chunks[0]
        for chunk in audio_chunks[1:]:
            combined_audio += chunk
            
        # Save temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            combined_audio.export(temp_file.name, format="wav")
            temp_path = temp_file.name
        
            try:
                # Run diarization
                diarization = self.pipeline(temp_path)
                
                # Extract speaker embeddings
                embeddings = {}
                durations = {}
                
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    if speaker not in embeddings:
                        embeddings[speaker] = []
                        durations[speaker] = 0
                    
                    # Track speaking duration to identify host vs guest
                    durations[speaker] += turn.end - turn.start
                    
                    # Extract audio segment for this speaker
                    segment = combined_audio[turn.start*1000:turn.end*1000]
                    if len(segment) > 0:  # Ensure segment has content
                        embeddings[speaker].append(segment)
                
                # Store speaker embeddings for future identification
                self.speaker_embeddings = {
                    speaker: self._compute_embedding(segments) 
                    for speaker, segments in embeddings.items()
                }
                
                # Determine roles (host vs guest) based on speaking time
                roles = {}
                if len(durations) >= 2:
                    # Sort speakers by duration
                    sorted_speakers = sorted(durations.items(), key=lambda x: x[1], reverse=True)
                    # Assign roles - host typically speaks more
                    roles[sorted_speakers[0][0]] = "host"
                    for i in range(1, len(sorted_speakers)):
                        roles[sorted_speakers[i][0]] = f"guest_{i}"
                elif len(durations) == 1:
                    # Only one speaker (monologue)
                    roles[list(durations.keys())[0]] = "host"
                    
                self.is_initialized = True
                self.speaker_roles = roles
                
                return {
                    "num_speakers": len(self.speaker_embeddings),
                    "speakers": [
                        {"id": speaker, "role": roles.get(speaker, "unknown")}
                        for speaker in self.speaker_embeddings.keys()
                    ]
                }
                
            finally:
                # Clean up
                os.unlink(temp_path)

    async def process_chunk(self, audio_chunk: AudioSegment) -> List[Dict]:
        """Process a single audio chunk and identify speakers"""
        if not self.is_initialized:
            raise RuntimeError("Speaker diarization not initialized. Run process_initial_chunks first.")
        
        # Save temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            audio_chunk.export(temp_file.name, format="wav")
            temp_path = temp_file.name
            
        try:
            # Run diarization
            diarization = self.pipeline(temp_path)
            
            # Match speakers with known embeddings
            segments = []
            for turn, _, speaker_id in diarization.itertracks(yield_label=True):
                # Extract audio segment
                segment = audio_chunk[turn.start*1000:turn.end*1000]
                if len(segment) == 0:
                    continue
                    
                # Match with known speakers if we have embeddings
                if self.speaker_embeddings:
                    embedding = self._compute_embedding([segment])
                    matched_speaker = self._match_speaker(embedding)
                else:
                    matched_speaker = speaker_id
                    
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": matched_speaker,
                    "role": self.speaker_roles.get(matched_speaker, "unknown")
                })
                
            return segments
            
        finally:
            # Clean up
            os.unlink(temp_path)
    
    def _compute_embedding(self, audio_segments: List[AudioSegment]) -> np.ndarray:
        """Compute embedding for a speaker from multiple audio segments"""
        # This is a simplified version - in production, you'd use a proper speaker embedding model
        # For now, we'll use a simple audio fingerprint
        combined = np.concatenate([
            np.array(segment.get_array_of_samples()) for segment in audio_segments
        ])
        # Simple fingerprint based on frequency characteristics
        return np.abs(np.fft.fft(combined[:min(len(combined), 44100)]))
    
    def _match_speaker(self, embedding: np.ndarray) -> str:
        """Match a new embedding with known speakers"""
        if not self.speaker_embeddings:
            return "speaker_0"
            
        # Calculate similarity with known speakers
        similarities = {}
        for speaker, known_embedding in self.speaker_embeddings.items():
            # Cosine similarity
            similarity = np.dot(embedding, known_embedding) / (
                np.linalg.norm(embedding) * np.linalg.norm(known_embedding)
            )
            similarities[speaker] = similarity
            
        # Return the most similar speaker
        return max(similarities.items(), key=lambda x: x[1])[0]
        