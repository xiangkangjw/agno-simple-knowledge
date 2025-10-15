"""Document indexing service - focused on document management operations."""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable

from .indexer import DocumentIndexer
from .config import config

logger = logging.getLogger(__name__)


class DocumentIndexingService:
    """Service focused solely on document indexing and management operations."""

    def __init__(self) -> None:
        """Initialize the document indexing service."""
        self.config = config
        self.indexer = DocumentIndexer()
        self._index_update_callbacks: List[Callable[[], None]] = []
        self._initialized = False

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
        """Refresh the entire document index."""
        if not self._initialized:
            raise RuntimeError("Service not initialized")

        try:
            logger.info("Starting index refresh...")
            self.indexer.refresh_index()

            # Notify that index has been updated
            self._notify_index_updated()

            stats = self.indexer.get_index_stats()

            logger.info("Index refresh completed")
            return {
                "success": True,
                "message": "Index refreshed successfully",
                "stats": stats
            }

        except Exception as exc:
            logger.error("Index refresh failed: %s", exc)
            return {
                "success": False,
                "error": str(exc)
            }

    async def add_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Add new documents to the index."""
        if not self._initialized:
            raise RuntimeError("Service not initialized")

        try:
            logger.info(f"Adding {len(file_paths)} documents...")

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

            self.indexer.add_documents(valid_paths)

            # Notify that index has been updated
            self._notify_index_updated()

            stats = self.indexer.get_index_stats()

            logger.info("Documents added successfully")
            return {
                "success": True,
                "message": f"Added {len(valid_paths)} documents",
                "stats": stats
            }

        except Exception as exc:
            logger.error("Failed to add documents: %s", exc)
            return {
                "success": False,
                "error": str(exc)
            }

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
        self._index_update_callbacks.clear()
        self._initialized = False