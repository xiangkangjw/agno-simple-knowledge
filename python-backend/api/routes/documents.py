"""Document management API routes."""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class AddDocumentsRequest(BaseModel):
    file_paths: List[str]

class SearchDocumentsRequest(BaseModel):
    query: str
    top_k: int = 10

@router.post("/refresh")
async def refresh_index(request: Request) -> Dict[str, Any]:
    """Start an asynchronous index refresh operation.

    Returns operation_id to track progress via GET /operations/{operation_id}
    """
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        if not knowledge_system.is_ready():
            raise HTTPException(status_code=503, detail="Knowledge system not ready")

        # Start async refresh operation
        result = await knowledge_system.refresh_index()
        return result

    except Exception as e:
        logger.error(f"Index refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add")
async def add_documents(
    request: Request,
    add_request: AddDocumentsRequest
) -> Dict[str, Any]:
    """Start an asynchronous add documents operation.

    Returns operation_id to track progress via GET /operations/{operation_id}
    """
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        if not knowledge_system.is_ready():
            raise HTTPException(status_code=503, detail="Knowledge system not ready")

        if not add_request.file_paths:
            raise HTTPException(status_code=400, detail="No file paths provided")

        # Start async add documents operation
        result = await knowledge_system.add_documents(add_request.file_paths)
        return result

    except Exception as e:
        logger.error(f"Add documents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search_documents(
    request: Request,
    search_request: SearchDocumentsRequest
) -> Dict[str, Any]:
    """Search for documents similar to the query."""
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        if not knowledge_system.is_ready():
            raise HTTPException(status_code=503, detail="Knowledge system not ready")

        if not search_request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        # Search documents via Agno knowledge
        results = knowledge_system.search_documents(
            search_request.query,
            search_request.top_k
        )

        return {
            "success": True,
            "query": search_request.query,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_document_stats(request: Request) -> Dict[str, Any]:
    """Get document index statistics."""
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        if not knowledge_system.is_ready():
            return {"status": "not_ready", "document_count": 0}

        stats = knowledge_system.document_service.get_index_stats()
        return stats

    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
