import logging

from app.services.firebase.firestore import Firestore


logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

store = Firestore(collection_name="ext_summarize")

async def get_history_handler(uid: str):
    return await store.get_by_field(
        field="uid",
        value=uid,
        order_by_field="createdAt",
        order_direction="DESC"
    )

async def get_history_by_id_handler(sessionId: str):
    return await store.get_by_id(doc_id=sessionId)

async def delete_history_by_id_handler(sessionId: str):
    return await store.delete(doc_id=sessionId)

async def delete_all_history_by_uid_handler(uid: str):
    return await store.delete_by_field(
        field="uid",
        value=uid
    )