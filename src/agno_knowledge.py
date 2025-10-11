"""Native Agno knowledge integration for read-only querying of existing LlamaIndex ChromaDB."""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.chroma import ChromaDb, SearchType

from .config import config

logger = logging.getLogger(__name__)

class AgnoKnowledgeManager:
    """Read-only interface to existing LlamaIndex ChromaDB using Agno's Knowledge class."""

    def __init__(self):
        """Initialize the Agno knowledge manager to connect to existing ChromaDB."""
        self.config = config
        self.knowledge: Optional[Knowledge] = None
        self._setup_knowledge()

    def _setup_knowledge(self) -> None:
        """Set up the Agno Knowledge instance to connect to existing LlamaIndex ChromaDB."""
        try:
            # Connect to existing ChromaDB created by LlamaIndex indexer
            # Use the same path and embedding model as the indexer
            vector_db = ChromaDb(
                collection="knowledge_base",  # Must match indexer collection name
                path=self.config.storage_path,  # Use same path as indexer
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(
                    id=self.config.embedding_model,  # Use same embedding model as indexer
                    api_key=self.config.get_openai_api_key()
                )
            )

            # Create Knowledge instance (read-only connection)
            self.knowledge = Knowledge(vector_db=vector_db)

            logger.info("Agno Knowledge connected to existing LlamaIndex ChromaDB")

        except Exception as e:
            logger.error(f"Failed to connect to existing ChromaDB: {e}")
            raise


    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the existing knowledge base.

        Returns:
            Dictionary with knowledge statistics
        """
        try:
            if not self.knowledge:
                return {
                    'status': 'Not connected',
                    'storage_path': 'N/A',
                    'collection_name': 'N/A'
                }

            # Return basic stats about the connection
            return {
                'status': 'Connected to existing ChromaDB',
                'storage_path': self.config.storage_path,
                'collection_name': self.config.collection_name,
                'note': 'Read-only connection to LlamaIndex database'
            }

        except Exception as e:
            logger.error(f"Error getting knowledge stats: {e}")
            return {
                'status': f'Error: {str(e)}',
                'storage_path': 'N/A',
                'collection_name': 'N/A'
            }

    def is_ready(self) -> bool:
        """Check if the knowledge manager is ready.

        Returns:
            True if ready, False otherwise
        """
        return self.knowledge is not None

    def get_knowledge_instance(self) -> Optional[Knowledge]:
        """Get the underlying Agno Knowledge instance.

        Returns:
            Knowledge instance or None if not initialized
        """
        return self.knowledge