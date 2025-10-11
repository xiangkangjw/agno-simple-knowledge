"""Native Agno knowledge integration for read-only querying of existing ChromaDB."""

import logging
from typing import Dict, Any, Optional

from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.chroma import ChromaDb

from .config import config

logger = logging.getLogger(__name__)


class AgnoKnowledgeManager:
    """Read-only interface to existing ChromaDB using Agno's Knowledge class."""

    def __init__(self) -> None:
        """Initialize the Agno knowledge manager."""
        self.config = config
        self.knowledge: Optional[Knowledge] = None
        self._setup_knowledge()

    def _setup_knowledge(self) -> None:
        """Create the Agno Knowledge instance using the existing ChromaDB store."""
        try:
            vector_db = ChromaDb(
                collection=self.config.collection_name,
                path=self.config.storage_path,
                persistent_client=True,
                embedder=OpenAIEmbedder(
                    id=self.config.embedding_model,
                    api_key=self.config.get_openai_api_key()
                ),
            )

            self.knowledge = Knowledge(vector_db=vector_db)
            logger.info("Connected Agno Knowledge to existing ChromaDB collection")

        except Exception as exc:
            logger.error("Failed to initialize Agno Knowledge: %s", exc)
            raise

    def get_knowledge_instance(self) -> Optional[Knowledge]:
        """Return the underlying Knowledge instance."""
        return self.knowledge

    def refresh(self) -> None:
        """Recreate the Knowledge connection after index updates."""
        self._setup_knowledge()

    def is_ready(self) -> bool:
        """Return True when the Knowledge instance is ready."""
        return self.knowledge is not None

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Return metadata about the Knowledge connection."""
        if not self.knowledge:
            return {
                "status": "Not connected",
                "storage_path": self.config.storage_path,
                "collection_name": self.config.collection_name,
            }

        return {
            "status": "Connected",
            "storage_path": self.config.storage_path,
            "collection_name": self.config.collection_name,
            "note": "Read-only connection managed by AgnoKnowledgeManager",
        }
