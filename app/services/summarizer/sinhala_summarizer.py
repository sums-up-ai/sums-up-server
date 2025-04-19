import torch
from transformers import MT5ForConditionalGeneration, MT5Tokenizer
from typing import List, Dict

class SinhalaSummarizer:
    def __init__(self, model_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = MT5Tokenizer.from_pretrained(model_path)
        self.model = MT5ForConditionalGeneration.from_pretrained(model_path).to(self.device)
        
    async def summarize_transcript(self, 
                                  transcript_segments: List[Dict], 
                                  mode: str = "full") -> Dict:
        """
        Summarize transcript segments
        
        Args:
            transcript_segments: List of transcript segments with speaker info
            mode: Summarization mode - 'full', 'guest_only', or 'key_points'
        """
        # Filter segments based on mode
        if mode == "guest_only":
            # Only include segments from guests
            filtered_segments = [
                segment for segment in transcript_segments
                if segment["role"].startswith("guest")
            ]
        else:
            filtered_segments = transcript_segments
            
        if not filtered_segments:
            return {"summary": "No relevant content to summarize."}
            
        # Combine text by speaker for better context
        speaker_texts = {}
        for segment in filtered_segments:
            speaker = segment["speaker"]
            if speaker not in speaker_texts:
                speaker_texts[speaker] = []
            speaker_texts[speaker].append(segment["text"])
        
        # Create input text with speaker roles
        input_text = ""
        for speaker, texts in speaker_texts.items():
            role = next((s["role"] for s in filtered_segments if s["speaker"] == speaker), "speaker")
            speaker_text = " ".join(texts)
            input_text += f"{role}: {speaker_text}\n\n"
            
        # Prepare for MT5
        # Add a prefix to guide the model
        if mode == "key_points":
            prefix = "ප්‍රධාන කරුණු සාරාංශය: "  # "Key points summary: " in Sinhala
        else:
            prefix = "සාරාංශය: "  # "Summary: " in Sinhala
            
        input_text = prefix + input_text
        
        # Tokenize and generate summary
        inputs = self.tokenizer(input_text, return_tensors="pt", max_length=1024, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate summary
        summary_ids = self.model.generate(
            **inputs,
            max_length=150,
            min_length=40,
            length_penalty=2.0,
            num_beams=4,
            early_stopping=True
        )
        
        summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        
        return {
            "summary": summary,
            "mode": mode,
            "processed_segments": len(filtered_segments)
        }
