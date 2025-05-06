import asyncio
from app.core.config import settings
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoConfig


request_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_REQUESTS)

def get_bert_request_semaphore() -> asyncio.Semaphore:
    return request_semaphore


def get_sin_bert_model_and_tokenizer():    
    tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_PATH_SIN_BERT)
    config = AutoConfig.from_pretrained(settings.MODEL_PATH_SIN_BERT)
    model = AutoModelForSequenceClassification.from_pretrained(settings.MODEL_PATH_SIN_BERT)

    return model, tokenizer, config