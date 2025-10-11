"""Chat API routes."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class QueryRequest(BaseModel):
    query: str

@router.post("/message")
async def chat_message(request: Request, chat_request: ChatRequest) -> Dict[str, Any]:
    """Process a chat message with the knowledge agent."""
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        if not knowledge_system.is_ready():
            raise HTTPException(status_code=503, detail="Knowledge system not ready")

        if not chat_request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        # Process chat message
        result = await knowledge_system.chat(chat_request.message)
        return result

    except Exception as e:
        logger.error(f"Chat message failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query")
async def query_documents(request: Request, query_request: QueryRequest) -> Dict[str, Any]:
    """Query documents directly (without agent processing)."""
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        if not knowledge_system.is_ready():
            raise HTTPException(status_code=503, detail="Knowledge system not ready")

        if not query_request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        # Query documents
        result = await knowledge_system.query_documents(query_request.query)
        return result

    except Exception as e:
        logger.error(f"Document query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))