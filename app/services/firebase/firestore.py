from app.core.firebase import db
from typing import Dict, List, Any, Optional, Tuple
from fastapi import HTTPException, status
from google.cloud.firestore import Query

class Firestore:
    def __init__(self, collection_name: str):
        self.collection = db.collection(collection_name)
    
    async def create(self, data: Dict[str, Any]) -> str:
        """Create a new document and return its ID"""
        try:
            doc_ref = self.collection.document()
            doc_ref.set(data)
            return doc_ref.id
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create document: {str(e)}"
            )
    
    async def get_all(self) -> List[Dict[str, Any]]:
        """Get all documents from collection"""
        try:
            docs = self.collection.stream()
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve documents: {str(e)}"
            )
    
    async def get_by_id(self, doc_id: str) -> Dict[str, Any]:
        """Get document by ID"""
        try:
            doc = self.collection.document(doc_id).get()
            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID {doc_id} not found"
                )
            return {"id": doc.id, **doc.to_dict()}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve document: {str(e)}"
            )
    
    async def update(self, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update document by ID"""
        try:
            doc_ref = self.collection.document(doc_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID {doc_id} not found"
                )
            doc_ref.update(data)
            return {"id": doc_id, **data}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update document: {str(e)}"
            )
    
    async def delete(self, doc_id: str) -> Dict[str, str]:
        """Delete document by ID"""
        try:
            doc_ref = self.collection.document(doc_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document with ID {doc_id} not found"
                )
            doc_ref.delete()
            return {"message": f"Document with ID {doc_id} deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document: {str(e)}"
            )
        

    async def get_by_field(
        self,
        field: str,
        value: Any,
        filter_conditions: Optional[List[Tuple[str, str, Any]]] = None,
        order_by_field: Optional[str] = None,
        order_direction: str = "ASC"
    ) -> List[Dict[str, Any]]:
        try:
            query = self.collection.where(field, "==", value)

            if filter_conditions:
                for field_path, op, val in filter_conditions:
                    query = query.where(field_path, op, val)

            if order_by_field:
                direction = Query.DESCENDING if order_direction.upper() == "DESC" else Query.ASCENDING
                query = query.order_by(order_by_field, direction=direction)

            return [{"id": doc.id, **doc.to_dict()} for doc in query.stream()]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query failed: {str(e)}"
            )

    async def delete_by_field(self, field: str, value: Any) -> Dict[str, Any]:
        """
        Delete all documents where `field` == `value`.
        Returns a summary of deletion.
        """
        try:
            query = self.collection.where(field, "==", value)
            docs = list(query.stream())

            if not docs:
                return {"message": f"No documents found with {field} == {value}"}

            batch_size = 500
            total_deleted = 0

            for i in range(0, len(docs), batch_size):
                batch = db.batch()
                batch_docs = docs[i:i+batch_size]
                for doc in batch_docs:
                    batch.delete(doc.reference)
                batch.commit()
                total_deleted += len(batch_docs)

            return {
                "message": f"Deleted {total_deleted} documents where {field} == {value}"
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete documents: {str(e)}"
            )