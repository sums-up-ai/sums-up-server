import asyncio
from app.core.config import settings
from transformers import MT5ForConditionalGeneration, MT5Tokenizer


request_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)

def get_request_semaphore() -> asyncio.Semaphore:
    return request_semaphore

def get_model_and_tokenizer():
    tokenizer = MT5Tokenizer.from_pretrained(settings.MODEL_PATH) # type: ignore
    model = MT5ForConditionalGeneration.from_pretrained(settings.MODEL_PATH) # type: ignore
    return model, tokenizer

def get_with_category_model_and_tokenizer():
    tokenizer = MT5Tokenizer.from_pretrained(settings.MODEL_PATH_WITH_CATEGORY) # type: ignore
    model = MT5ForConditionalGeneration.from_pretrained(settings.MODEL_PATH_WITH_CATEGORY) # type: ignore
    return model, tokenizer