"""Central knowledge management system coordinator."""

import logging
from typing import Dict, List, Any, Optional
import asyncio
from pathlib import Path

# Import our existing modules (we'll copy them here)
from .config import config
from .indexer import DocumentIndexer
from .query_engine import KnowledgeQueryEngine
from .chat_agent import KnowledgeAgent

logger = logging.getLogger(__name__)

class KnowledgeSystem:
    """Main coordinator for the knowledge management system."""

    def __init__(self):
        """Initialize the knowledge system."""
        self.config = config
        self.indexer: Optional[DocumentIndexer] = None
        self.query_engine: Optional[KnowledgeQueryEngine] = None
        self.chat_agent: Optional[KnowledgeAgent] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all components of the knowledge system."""
        if self._initialized:
            return

        logger.info("Initializing knowledge system...")

        try:
            # Initialize components
            self.indexer = DocumentIndexer()
            self.query_engine = KnowledgeQueryEngine(self.indexer)

            # Initialize query engine (this loads or creates the index)
            await asyncio.get_event_loop().run_in_executor(
                None, self.query_engine.initialize
            )

            # Initialize chat agent
            self.chat_agent = KnowledgeAgent()

            self._initialized = True
            logger.info("Knowledge system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize knowledge system: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up knowledge system...")
        # Add any cleanup logic here

    def is_ready(self) -> bool:
        """Check if the system is ready to process requests."""
        return (
            self._initialized and
            self.indexer is not None and
            self.query_engine is not None and
            self.chat_agent is not None
        )

    async def get_system_status(self) -> Dict[str, Any]:
        """Get the current system status."""
        if not self.is_ready():
            return {
                "status": "not_ready",
                "initialized": self._initialized,
                "components": {
                    "indexer": self.indexer is not None,
                    "query_engine": self.query_engine is not None,
                    "chat_agent": self.chat_agent is not None
                }
            }

        # Get index stats
        stats = await asyncio.get_event_loop().run_in_executor(
            None, self.indexer.get_index_stats
        )

        return {
            "status": "ready",
            "initialized": True,
            "index_stats": stats,
            "target_directories": self.config.target_directories,
            "supported_formats": self.config.file_extensions
        }

    async def refresh_index(self) -> Dict[str, Any]:
        """Refresh the document index."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            logger.info("Starting index refresh...")

            # Run refresh in executor to avoid blocking
            index = await asyncio.get_event_loop().run_in_executor(
                None, self.indexer.refresh_index
            )

            # Reinitialize query engine
            await asyncio.get_event_loop().run_in_executor(
                None, self.query_engine.initialize
            )

            stats = await asyncio.get_event_loop().run_in_executor(
                None, self.indexer.get_index_stats
            )

            logger.info("Index refresh completed")
            return {
                "success": True,
                "message": "Index refreshed successfully",
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Index refresh failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def add_documents(self, file_paths: List[str]) -> Dict[str, Any]:
        """Add documents to the index."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            logger.info(f"Adding {len(file_paths)} documents...")

            # Run in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, self.indexer.add_documents, file_paths
            )

            # Reinitialize query engine
            await asyncio.get_event_loop().run_in_executor(
                None, self.query_engine.initialize
            )

            stats = await asyncio.get_event_loop().run_in_executor(
                None, self.indexer.get_index_stats
            )

            logger.info("Documents added successfully")
            return {
                "success": True,
                "message": f"Added {len(file_paths)} documents",
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def query_documents(self, query: str) -> Dict[str, Any]:
        """Query the document index."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            logger.info(f"Processing query: {query}")

            # Run query in executor
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.query_engine.query, query
            )

            if result:
                logger.info("Query processed successfully")
                return {
                    "success": True,
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to process query"
                }

        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def chat(self, message: str) -> Dict[str, Any]:
        """Process a chat message."""
        if not self.is_ready():
            raise RuntimeError("System not ready")

        try:
            logger.info(f"Processing chat message: {message}")

            # Run chat in executor
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.chat_agent.chat, message
            )

            logger.info("Chat message processed successfully")
            return {
                "success": True,
                "response": response
            }

        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }