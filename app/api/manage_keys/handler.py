import logging
from app.services.firebase.firestore import Firestore
from datetime import datetime
import random
import string

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

store = Firestore(collection_name="api_keys")

def generate_key() -> str:
    key = "sk_" + ''.join(random.choices(string.ascii_letters + string.digits, k=40))
    return key

async def get_keys_handler(uid: str):
    return await store.get_by_field(
        field="uid",
        value=uid,
        order_by_field="createdAt",
        order_direction="DESC"
    )

async def create_key_handler(uid: str):
    key = generate_key()
    data = {
        "key": key,
        "uid": uid,
        "createdAt": datetime.utcnow().isoformat()
    }
    doc_id = await store.create(data)
    return {**data, "id": doc_id}

async def revoke_key_handler(key_id: str, uid: str):    
    doc = await store.get_by_id(doc_id=key_id)
    if not doc or doc.get("uid") != uid:
        return False
    return await store.delete(doc_id=key_id)
