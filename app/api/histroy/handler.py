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