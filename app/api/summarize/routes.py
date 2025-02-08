from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from pydantic import BaseModel
import torch
import asyncio

model_path = "C:\\Users\\Janithpm\\Desktop\\sums-up-server\\app\\api\\summarize\\summ-model"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

summarize_router = APIRouter(tags=['summarize'])

class SummarizationRequest(BaseModel):
    text: str

async def generate_summary_stream(text: str, max_length: int = 150, min_length: int = 30):
    input_prompt = "summarize: " + text.strip()
    input_ids = tokenizer.encode(input_prompt, return_tensors="pt", max_length=512, truncation=True)
    
    # Generate with beam search
    output_ids = model.generate(
        input_ids,
        max_length=max_length,
        min_length=min_length,
        num_beams=4,
        early_stopping=True,
        no_repeat_ngram_size=2,
        return_dict_in_generate=True,
        output_scores=True,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    
    # Get the generated sequence
    generated_sequence = output_ids.sequences[0]
    
    # Stream the tokens gradually
    current_summary = ""
    for i in range(1, len(generated_sequence)):
        token_ids = generated_sequence[:i+1]
        current_token = tokenizer.decode(token_ids, skip_special_tokens=True)
        if current_token.strip() and current_token != current_summary:
            yield {"data": current_token[len(current_summary):]}
            current_summary = current_token
            await asyncio.sleep(0.05)

@summarize_router.post("/generate-stream",)
async def generate_stream(request: SummarizationRequest):
    return EventSourceResponse(
        generate_summary_stream(request.text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        })

@summarize_router.post("/generate")
async def summarize_endpoint(request: SummarizationRequest):
    summary = ""
    async for chunk in generate_summary_stream(request.text):
        summary += chunk["data"]
    return {"summary": summary}
