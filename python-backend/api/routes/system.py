"""System and health check API routes."""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any

router = APIRouter()

@router.get("/status")
async def get_system_status(request: Request) -> Dict[str, Any]:
    """Get the current system status and statistics."""
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        status = await knowledge_system.get_system_status()
        return status

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "knowledge-management-api"}

@router.get("/config")
async def get_config(request: Request) -> Dict[str, Any]:
    """Get configuration information (non-sensitive)."""
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        config = knowledge_system.config
        return {
            "target_directories": config.target_directories,
            "file_extensions": config.file_extensions,
            "max_results": config.max_results,
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))