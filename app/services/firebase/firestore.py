from core.firebase import db
from typing import Dict, List, Any, Optional
from fastapi import HTTPException, status

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
