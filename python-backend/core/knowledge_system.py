"""Central knowledge management system coordinator - simplified facade."""

import logging
from typing import Dict, List, Any, Optional
import asyncio

from .config import config
from .document_service import DocumentIndexingService
from .chat_service import KnowledgeChatService
from .agno_knowledge import AgnoKnowledgeManager
from .operation_manager import OperationManager

logger = logging.getLogger(__name__)


class KnowledgeSystem:
    """Simplified coordinator facade for the knowledge management system."""

    def __init__(self) -> None:
        """Initialize the knowledge system."""
        self.config = config
        self.operation_manager = OperationManager()
        self.knowledge_manager: Optional[AgnoKnowledgeManager] = None
        self.document_service: Optional[DocumentIndexingService] = None
        self.chat_service: Optional[KnowledgeChatService] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all components of the knowledge system."""
        if self._initialized:
            return

        logger.info("Initializing knowledge system...")

        try:
            # Initialize shared knowledge manager
            self.knowledge_manager = AgnoKnowledgeManager()

            # Initialize document service with operation manager
            self.document_service = DocumentIndexingService(self.operation_manager)
            await self.document_service.initialize()

            # Initialize chat service
            self.chat_service = KnowledgeChatService(self.knowledge_manager)
            await self.chat_service.initialize()

            # Set up event-driven updates: document service notifies chat service
            self.document_service.on_index_updated(self.chat_service.on_knowledge_updated)

            self._initialized = True
            logger.info("Knowledge system initialized successfully")

        except Exception as exc:
            logger.error("Failed to initialize knowledge system: %s", exc)
            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up knowledge system...")

        if self.document_service:
            await self.document_service.cleanup()

        if self.chat_service:
            await self.chat_service.cleanup()

        self._initialized = False

    def is_ready(self) -> bool:
        """Check if the system is ready to process requests."""
        return (
            self._initialized
            and self.document_service is not None
            and self.chat_service is not None
            and self.knowledge_manager is not None
            and self.document_service.is_ready()
            and self.chat_service.is_ready()
        )

    async def get_system_status(self) -> Dict[str, Any]:
        """Get the current system status."""
        if not self.is_ready():
            return {
                "status": "not_ready",
                "initialized": self._initialized,
                "components": {
                    "document_service": self.document_service is not None,
                    "chat_service": self.chat_service is not None,
                    "knowledge_manager": self.knowledge_manager is not None,
                }
            }

        # Get stats from services
        index_stats = self.document_service.get_index_stats()
        chat_stats = self.chat_service.get_service_stats()
        knowledge_stats = self.knowledge_manager.get_knowledge_stats()

        return {
            "status": "ready",
            "initialized": True,
            "architecture": "Team-based with specialized services",
            "index_stats": index_stats,
            "chat_stats": chat_stats,
            "knowledge_stats": knowledge_stats,
            "target_directories": self.config.target_directories,
            "supported_formats": self.config.file_extensions,
        }

    async def refresh_index(self) -> Dict[str, Any]:
        """Refresh the document index."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            logger.info("Starting index refresh...")
            result = await self.document_service.refresh_index()
            logger.info("Index refresh completed")
            return result

        except Exception as exc:
            logger.error("Index refresh failed: %s", exc)
            return {
                "success": False,
                "error": str(exc)
            }

    async def add_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Add documents to the index."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            logger.info(f"Adding {len(file_paths)} documents...")
            result = await self.document_service.add_documents(file_paths)
            logger.info("Documents added successfully")
            return result

        except Exception as exc:
            logger.error("Failed to add documents: %s", exc)
            return {
                "success": False,
                "error": str(exc)
            }

    async def query_documents(self, query: str) -> Dict[str, Any]:
        """Query the document index."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            logger.info("Processing document query: %s", query)
            # Directly await the async helper method
            result = await self._run_document_query(query)

            if result is None:
                return {
                    "success": False,
                    "error": "Failed to process query",
                }

            logger.info("Query processed successfully")
            return {"success": True, "result": result}

        except Exception as exc:
            logger.error("Query failed: %s", exc)
            return {
                "success": False,
                "error": str(exc)
            }

    async def chat(self, message: str) -> Dict[str, Any]:
        """Process a chat message."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            logger.info("Processing chat message: %s", message)
            response = await self.chat_service.chat(message)

            logger.info("Chat message processed successfully")
            return {"success": True, "response": response}

        except Exception as exc:
            logger.error("Chat failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def search_documents(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search documents using the chat service."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            return await self.chat_service.search_documents(query, top_k)
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return []

    async def _run_document_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Asynchronously run a document query using the chat service."""
        try:
            # Get search results
            documents = await self.search_documents(query)

            sources: List[Dict[str, Any]] = []
            for doc in documents:
                text_preview = doc["text"][:200] + ("..." if len(doc["text"]) > 200 else "")
                sources.append(
                    {
                        "text": text_preview,
                        "full_text": doc["text"],
                        "score": doc["score"],
                        "metadata": doc["metadata"],
                        "document_id": doc["document_id"],
                    }
                )

            # Get chat response
            chat_result = await self.chat(query)
            answer = chat_result.get("response", "No response available")

            return {
                "answer": answer,
                "sources": sources,
                "query": query,
                "metadata": {
                    "source_count": len(sources),
                    "knowledge_status": "ready" if sources else "no_results",
                    "architecture": "team-based",
                },
            }

        except Exception as e:
            logger.error(f"Document query failed: {e}")
            return None
