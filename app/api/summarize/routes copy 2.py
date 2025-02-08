from app.services.web_socket_manager.web_sockect_manager import WSConnectionManager
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from pydantic import BaseModel
from app.services.web_socket_manager.web_sockect_manager import WSConnectionManager
import asyncio

# MODEL_NAME = "./summ-model"
# tokenizer = MT5Tokenizer.from_pretrained(MODEL_NAME)
# model = MT5ForConditionalGeneration.from_pretrained(MODEL_NAME)

model_path = "C:\\Users\\Janithpm\\Desktop\\sums-up-server\\app\\api\\summarize\\summ-model"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

websocket_manager = WSConnectionManager()

summarize_router = APIRouter(tags=['summarize'])

class SummarizationRequest(BaseModel):
    text: str

def summarize_text(text: str, max_length: int = 150, min_length: int = 30) -> str:
    print("summarization started")
    print(text[:10])
    input_prompt = "summarize: " + text.strip()
    input_ids = tokenizer.encode(input_prompt, return_tensors="pt", max_length=512, truncation=True)
    summary_ids = model.generate(input_ids,
                                 num_beams=4,
                                 max_length=max_length,
                                 min_length=min_length,
                                 early_stopping=True)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary

# @summarize_router.websocket("/ws/generate")
# async def websocket_summarize(websocket: WebSocket):
#     try:
#         user_id = websocket.query_params.get("user_id", "default")
#         await websocket_manager.connect(user_id, websocket)
#         while True:
#             input_text = await websocket.receive_text()
#             print(f"Received text from {user_id}")
#             summary = summarize_text(input_text)
#             sentences = summary.split('. ')
#             await websocket_manager.send_personal_message(summary, user_id)
#             await asyncio.sleep(2)

#             # for sentence in sentences:
#             #     if sentence:
#             #         output_chunk = sentence.strip()
#             #         if not output_chunk.endswith('.'):
#             #             output_chunk += '.'
#     except WebSocketDisconnect:
#         websocket_manager.disconnect(user_id)
#         print(f"Client {user_id} disconnected.")

@summarize_router.post("/generate")
async def summarize_endpoint(request: SummarizationRequest):
    summary = summarize_text(request.text)
    return {"summary": summary}
