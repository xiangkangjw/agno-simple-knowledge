"""Knowledge chat service - focused on chat operations and agent management."""

import logging
from typing import Optional, Dict, Any, List

from .config import config
from .agno_knowledge import AgnoKnowledgeManager
from .knowledge_team import KnowledgePlanningTeam

logger = logging.getLogger(__name__)


class KnowledgeChatService:
    """Service focused solely on chat operations and knowledge agent management."""

    def __init__(self, knowledge_manager: Optional[AgnoKnowledgeManager] = None) -> None:
        """Initialize the knowledge chat service."""
        self.config = config
        self.knowledge_manager = knowledge_manager or AgnoKnowledgeManager()
        self.planning_team: Optional[KnowledgePlanningTeam] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the knowledge chat service."""
        if self._initialized:
            return

        logger.info("Initializing knowledge chat service...")

        try:
            # Ensure knowledge manager is ready
            if not self.knowledge_manager.is_ready():
                raise RuntimeError("Knowledge manager is not ready")

            # Initialize the planning team
            self.planning_team = KnowledgePlanningTeam(self.knowledge_manager)

            if not self.planning_team.is_ready():
                raise RuntimeError("Failed to initialize knowledge planning team")

            self._initialized = True
            logger.info("Knowledge chat service initialized successfully")

        except Exception as exc:
            logger.error("Failed to initialize knowledge chat service: %s", exc)
            raise

    def on_knowledge_updated(self) -> None:
        """Callback for when the knowledge base is updated."""
        if self._initialized and self.planning_team:
            try:
                logger.info("Refreshing chat service due to knowledge update...")
                self.planning_team.refresh_knowledge()
                logger.info("Chat service refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh chat service: {e}")

    async def chat(self, message: str, stream: bool = False) -> str:
        """Process a chat message and return the response."""
        if not self._initialized:
            raise RuntimeError("Chat service not initialized")

        if not self.planning_team:
            return "Error: Knowledge planning team is not available."

        try:
            logger.info(f"Processing chat message: {message}")
            response = await self.planning_team.chat(message, stream=stream)
            return response

        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def is_ready(self) -> bool:
        """Check if the service is ready to process requests."""
        return (
            self._initialized
            and self.planning_team is not None
            and self.planning_team.is_ready()
        )

    def get_service_stats(self) -> Dict[str, Any]:
        """Get statistics about the chat service."""
        if not self._initialized:
            return {"status": "Service not initialized"}

        if not self.planning_team:
            return {"status": "Planning team not available"}

        team_stats = self.planning_team.get_team_stats()

        return {
            "status": "Ready",
            "service_type": "Team-based Knowledge Chat",
            "initialized": True,
            "team_stats": team_stats,
        }

    async def search_documents(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search documents using the knowledge base."""
        if not self._initialized:
            raise RuntimeError("Chat service not initialized")

        if not self.knowledge_manager.is_ready():
            logger.error("Knowledge manager not ready for search")
            return []

        knowledge = self.knowledge_manager.get_knowledge_instance()
        if not knowledge:
            logger.error("Knowledge instance not available for search")
            return []

        try:
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

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up knowledge chat service...")
        self.planning_team = None
        self._initialized = False