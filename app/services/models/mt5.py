import asyncio
from app.core.config import settings

model = None
tokenizer = None

request_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)

def get_request_semaphore() -> asyncio.Semaphore:
    return request_semaphore

def get_model_and_tokenizer():
    global model, tokenizer

    if model is None or tokenizer is None:
        from transformers import MT5ForConditionalGeneration, MT5Tokenizer
        
        tokenizer = MT5Tokenizer.from_pretrained(settings.MODEL_PATH) # type: ignore
        model = MT5ForConditionalGeneration.from_pretrained(settings.MODEL_PATH) # type: ignore

    return model, tokenizer