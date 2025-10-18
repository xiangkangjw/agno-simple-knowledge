"""Operations API routes for tracking long-running operations."""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/operations/{operation_id}")
async def get_operation_status(
    request: Request,
    operation_id: str
) -> Dict[str, Any]:
    """Get the status of a specific operation.

    Args:
        request: FastAPI request object
        operation_id: The operation ID to check

    Returns:
        Operation details including status, progress, and results
    """
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        if not knowledge_system.is_ready():
            raise HTTPException(status_code=503, detail="Knowledge system not ready")

        # Get operation from document service
        operation = await knowledge_system.document_service.operation_manager.get_operation(
            operation_id
        )

        if not operation:
            raise HTTPException(status_code=404, detail=f"Operation {operation_id} not found")

        return {
            "success": True,
            "operation": operation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get operation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/operations")
async def list_operations(
    request: Request,
    limit: int = 50,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """List recent operations.

    Args:
        request: FastAPI request object
        limit: Maximum number of operations to return (default 50)
        status: Filter by status (optional)

    Returns:
        List of recent operations
    """
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        if not knowledge_system.is_ready():
            raise HTTPException(status_code=503, detail="Knowledge system not ready")

        # List operations from document service
        operations = await knowledge_system.document_service.operation_manager.list_operations(
            limit=limit,
            status=status
        )

        return {
            "success": True,
            "operations": operations,
            "count": len(operations)
        }

    except Exception as e:
        logger.error(f"Failed to list operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/operations/{operation_id}/cancel")
async def cancel_operation(
    request: Request,
    operation_id: str
) -> Dict[str, Any]:
    """Cancel a running operation.

    Args:
        request: FastAPI request object
        operation_id: The operation ID to cancel

    Returns:
        Cancellation confirmation
    """
    try:
        knowledge_system = request.app.state.knowledge_system
        if not knowledge_system:
            raise HTTPException(status_code=503, detail="Knowledge system not available")

        if not knowledge_system.is_ready():
            raise HTTPException(status_code=503, detail="Knowledge system not ready")

        # Check if operation exists
        operation = await knowledge_system.document_service.operation_manager.get_operation(
            operation_id
        )

        if not operation:
            raise HTTPException(status_code=404, detail=f"Operation {operation_id} not found")

        # Cancel the operation
        await knowledge_system.document_service.operation_manager.cancel_operation(operation_id)

        # Try to cancel the background task if it's still running
        if operation_id in knowledge_system.document_service._running_operations:
            task = knowledge_system.document_service._running_operations[operation_id]
            if not task.done():
                task.cancel()

        return {
            "success": True,
            "message": f"Operation {operation_id} cancelled"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
