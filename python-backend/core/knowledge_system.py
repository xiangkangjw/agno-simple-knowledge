"""Central knowledge management system coordinator."""

import logging
from typing import Dict, List, Any, Optional
import asyncio

from .config import config
from .indexer import DocumentIndexer
from .agno_knowledge import AgnoKnowledgeManager
from .chat_agent import KnowledgeAgent

logger = logging.getLogger(__name__)


class KnowledgeSystem:
    """Main coordinator for the knowledge management system."""

    def __init__(self) -> None:
        """Initialize the knowledge system."""
        self.config = config
        self.indexer: Optional[DocumentIndexer] = None
        self.knowledge_manager: Optional[AgnoKnowledgeManager] = None
        self.chat_agent: Optional[KnowledgeAgent] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all components of the knowledge system."""
        if self._initialized:
            return

        logger.info("Initializing knowledge system...")

        try:
            loop = asyncio.get_event_loop()

            # Initialize components
            self.indexer = DocumentIndexer()

            # Ensure the index exists so Knowledge can attach to it
            try:
                await loop.run_in_executor(None, self.indexer.get_or_create_index)
            except ValueError as exc:
                logger.warning("No documents available during initialization: %s", exc)

            self.knowledge_manager = AgnoKnowledgeManager()
            self.chat_agent = KnowledgeAgent(self.knowledge_manager)

            self._initialized = True
            logger.info("Knowledge system initialized successfully")

        except Exception as exc:
            logger.error("Failed to initialize knowledge system: %s", exc)
            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up knowledge system...")
        # Add any cleanup logic here

    def is_ready(self) -> bool:
        """Check if the system is ready to process requests."""
        return (
            self._initialized
            and self.indexer is not None
            and self.knowledge_manager is not None
            and self.chat_agent is not None
            and self.knowledge_manager.is_ready()
        )

    async def get_system_status(self) -> Dict[str, Any]:
        """Get the current system status."""
        if not self.is_ready():
            return {
                "status": "not_ready",
                "initialized": self._initialized,
                "components": {
                    "indexer": self.indexer is not None,
                    "knowledge_manager": self.knowledge_manager is not None,
                    "chat_agent": self.chat_agent is not None,
                }
            }

        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(None, self.indexer.get_index_stats)
        knowledge_stats = self.knowledge_manager.get_knowledge_stats()

        return {
            "status": "ready",
            "initialized": True,
            "index_stats": stats,
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

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.indexer.refresh_index)

            await loop.run_in_executor(None, self.knowledge_manager.refresh)
            self.chat_agent = KnowledgeAgent(self.knowledge_manager)

            stats = await loop.run_in_executor(None, self.indexer.get_index_stats)

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
        """Add documents to the index."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            logger.info(f"Adding {len(file_paths)} documents...")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.indexer.add_documents, file_paths)

            await loop.run_in_executor(None, self.knowledge_manager.refresh)
            self.chat_agent = KnowledgeAgent(self.knowledge_manager)

            stats = await loop.run_in_executor(None, self.indexer.get_index_stats)

            logger.info("Documents added successfully")
            return {
                "success": True,
                "message": f"Added {len(file_paths)} documents",
                "stats": stats
            }

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
            # Directly await the async chat method
            response = await self.chat_agent.chat(message)

            logger.info("Chat message processed successfully")
            return {"success": True, "response": response}

        except Exception as exc:
            logger.error("Chat failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def search_documents(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search documents using the Agno knowledge manager."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        knowledge = self.knowledge_manager.get_knowledge_instance()
        if not knowledge:
            logger.error("Knowledge instance not available for search")
            return []

        results = knowledge.search(
            query=query,
            max_results=top_k or self.config.max_results,
        )

        formatted: List[Dict[str, Any]] = []
        for doc in results:
            formatted.append(
                {
                    "text": doc.content,
                    "score": doc.reranking_score,
                    "metadata": doc.meta_data,
                    "document_id": doc.id,
                }
            )

        return formatted

    async def _run_document_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Asynchronously run a document query."""
        knowledge = self.knowledge_manager.get_knowledge_instance()
        if not knowledge:
            logger.error("Knowledge instance not ready for querying")
            return None

        # Run knowledge search in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(
            None,
            lambda: knowledge.search(query=query, max_results=self.config.max_results)
        )

        sources: List[Dict[str, Any]] = []
        for doc in documents:
            text_preview = doc.content[:200] + ("..." if len(doc.content) > 200 else "")
            sources.append(
                {
                    "text": text_preview,
                    "full_text": doc.content,
                    "score": doc.reranking_score,
                    "metadata": doc.meta_data,
                    "document_id": doc.id,
                }
            )

        # Use the async chat method
        answer = await self.chat_agent.chat(query)

        return {
            "answer": answer,
            "sources": sources,
            "query": query,
            "metadata": {
                "source_count": len(sources),
                "knowledge_status": "ready" if sources else "no_results",
            },
        }
