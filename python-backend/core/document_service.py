"""Document indexing service - focused on document management operations."""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from .indexer import DocumentIndexer
from .operation_manager import OperationManager
from .config import config

logger = logging.getLogger(__name__)


class DocumentIndexingService:
    """Service focused solely on document indexing and management operations."""

    def __init__(self, operation_manager: Optional[OperationManager] = None) -> None:
        """Initialize the document indexing service.

        Args:
            operation_manager: Optional OperationManager instance for LRO tracking
        """
        self.config = config
        self.indexer = DocumentIndexer()
        self.operation_manager = operation_manager or OperationManager()
        self._index_update_callbacks: List[Callable[[], None]] = []
        self._initialized = False
        self._running_operations: Dict[str, asyncio.Task] = {}

    def on_index_updated(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when the index is updated."""
        self._index_update_callbacks.append(callback)

    def _notify_index_updated(self) -> None:
        """Notify all registered callbacks that the index has been updated."""
        for callback in self._index_update_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in index update callback: {e}")

    async def initialize(self) -> None:
        """Initialize the document indexing service."""
        if self._initialized:
            return

        logger.info("Initializing document indexing service...")

        try:
            # Ensure the index exists (creates if needed)
            self.indexer.get_or_create_index()
            self._initialized = True
            logger.info("Document indexing service initialized successfully")

        except ValueError as exc:
            logger.warning("No documents available during initialization: %s", exc)
            self._initialized = True

        except Exception as exc:
            logger.error("Failed to initialize document indexing service: %s", exc)
            raise

    def is_ready(self) -> bool:
        """Check if the service is ready to process requests."""
        return self._initialized

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index."""
        if not self._initialized:
            return {"status": "Service not initialized", "document_count": 0}

        return self.indexer.get_index_stats()

    async def refresh_index(self) -> Dict[str, Any]:
        """Start an asynchronous index refresh operation.

        Returns:
            Operation info with operation_id to track progress
        """
        if not self._initialized:
            raise RuntimeError("Service not initialized")

        # Create operation
        operation_id = await self.operation_manager.create_operation('refresh_index')

        # Start background task
        task = asyncio.create_task(self._refresh_index_background(operation_id))
        self._running_operations[operation_id] = task

        logger.info(f"Started async index refresh: {operation_id}")
        return {
            "success": True,
            "operation_id": operation_id,
            "message": "Index refresh started",
            "status": "pending"
        }

    async def _refresh_index_background(self, operation_id: str) -> None:
        """Background task for index refresh.

        Args:
            operation_id: Operation ID to track
        """
        try:
            await self.operation_manager.start_operation(operation_id)

            logger.info(f"Starting index refresh for operation {operation_id}...")
            # Run the blocking refresh in a thread pool
            await asyncio.to_thread(self.indexer.refresh_index)

            # Notify that index has been updated
            self._notify_index_updated()

            # Get stats and complete operation
            stats = self.indexer.get_index_stats()
            await self.operation_manager.complete_operation(operation_id, stats)

            logger.info(f"Index refresh completed for operation {operation_id}")

        except Exception as exc:
            error_msg = str(exc)
            logger.error(f"Index refresh failed for operation {operation_id}: {exc}")
            await self.operation_manager.fail_operation(operation_id, error_msg)

        finally:
            # Clean up task reference
            self._running_operations.pop(operation_id, None)

    async def add_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Start an asynchronous add documents operation.

        Args:
            file_paths: List of file paths to add

        Returns:
            Operation info with operation_id to track progress
        """
        if not self._initialized:
            raise RuntimeError("Service not initialized")

        # Validate file paths
        valid_paths = []
        for path in file_paths:
            if Path(path).exists():
                valid_paths.append(path)
            else:
                logger.warning(f"File not found: {path}")

        if not valid_paths:
            return {
                "success": False,
                "error": "No valid file paths provided"
            }

        # Create operation
        operation_id = await self.operation_manager.create_operation(
            'add_documents',
            total_items=len(valid_paths)
        )

        # Start background task
        task = asyncio.create_task(self._add_documents_background(operation_id, valid_paths))
        self._running_operations[operation_id] = task

        logger.info(f"Started async add documents: {operation_id}")
        return {
            "success": True,
            "operation_id": operation_id,
            "message": f"Adding {len(valid_paths)} documents",
            "status": "pending"
        }

    async def _add_documents_background(self, operation_id: str, file_paths: List[str]) -> None:
        """Background task for adding documents.

        Args:
            operation_id: Operation ID to track
            file_paths: List of file paths to add
        """
        try:
            await self.operation_manager.start_operation(operation_id)

            logger.info(f"Adding {len(file_paths)} documents for operation {operation_id}...")
            # Run the blocking add_documents in a thread pool
            await asyncio.to_thread(self.indexer.add_documents, file_paths)

            # Notify that index has been updated
            self._notify_index_updated()

            # Get stats and complete operation
            stats = self.indexer.get_index_stats()
            await self.operation_manager.complete_operation(operation_id, stats)

            logger.info(f"Documents added for operation {operation_id}")

        except Exception as exc:
            error_msg = str(exc)
            logger.error(f"Failed to add documents for operation {operation_id}: {exc}")
            await self.operation_manager.fail_operation(operation_id, error_msg)

        finally:
            # Clean up task reference
            self._running_operations.pop(operation_id, None)

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return self.config.file_extensions

    def get_target_directories(self) -> List[str]:
        """Get list of target directories for indexing."""
        return self.config.target_directories

    async def scan_for_new_documents(self) -> List[str]:
        """Scan target directories for documents that aren't indexed yet."""
        if not self._initialized:
            raise RuntimeError("Service not initialized")

        try:
            # Get all documents from target directories
            all_docs = self.indexer._get_documents_from_directories()

            # For now, return all found documents
            # In a more advanced version, we could track which are already indexed
            logger.info(f"Found {len(all_docs)} documents in target directories")
            return all_docs

        except Exception as exc:
            logger.error("Failed to scan for documents: %s", exc)
            return []

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up document indexing service...")

        # Cancel any running operations
        for task in self._running_operations.values():
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._running_operations:
            await asyncio.gather(*self._running_operations.values(), return_exceptions=True)

        # Clean up old operations from database
        await self.operation_manager.cleanup_old_operations()

        self._index_update_callbacks.clear()
        self._initialized = False