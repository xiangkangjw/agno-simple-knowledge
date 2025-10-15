"""Chat agent using Agno framework with native knowledge integration."""

import asyncio
import logging
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from .config import config
from .agno_knowledge import AgnoKnowledgeManager

logger = logging.getLogger(__name__)


class KnowledgeAgent:
    """Main chat agent for the knowledge management system."""

    def __init__(self, knowledge_manager: Optional[AgnoKnowledgeManager] = None) -> None:
        """Initialize the knowledge agent."""
        self.config = config
        self.knowledge_manager = knowledge_manager or AgnoKnowledgeManager()
        self.agent: Optional[Agent] = None
        self._setup_agent()

    def _setup_agent(self) -> None:
        """Set up the Agno agent with knowledge tools and configuration."""
        try:
            knowledge = self.knowledge_manager.get_knowledge_instance()
            if not knowledge:
                raise ValueError("Failed to initialize Agno Knowledge instance")

            knowledge_tools = KnowledgeTools(
                knowledge=knowledge,
                enable_think=True,
                enable_search=True,
                enable_analyze=True,
                add_few_shot=True,
            )
            reasoning_tools = ReasoningTools(
                enable_think=True,
                enable_analyze=True,
                add_few_shot=True,
            )

            model = OpenAIChat(
                id=self.config.openai_model,
                api_key=self.config.get_openai_api_key(),
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            self.agent = Agent(
                model=model,
                knowledge=knowledge,
                search_knowledge=True,
                tools=[knowledge_tools, reasoning_tools],
                name="Knowledge Assistant",
                role="Document Search and Q&A Assistant",
                instructions="""You are a helpful knowledge assistant with read-only access to an indexed document database.

Your capabilities:
1. Search through indexed documents with intelligent retrieval
2. Use the dedicated reasoning tools (`think` and `analyze`) to work through complex questions
3. Analyze document content for deeper insights
4. Provide detailed answers with relevant source citations
5. Explain your reasoning when appropriate

Important limitations:
- You have READ-ONLY access to the knowledge base
- Indexing and document management are handled by separate services

When users ask questions:
- Search the indexed knowledge before answering
- Call the reasoning tools to plan and assess steps before finalizing a response
- Use the analyze tool to extract key insights from retrieved passages
- Provide comprehensive answers and cite your sources
- Clearly state when information is missing or requires re-indexing

Guidelines:
- Distinguish between knowledge base content and general knowledge
- Be transparent about limitations
- Offer actionable suggestions when helpful""",
                markdown=True,
                add_history_to_context=True,
                read_chat_history=True,
                debug_mode=self.config.get("system.enable_debug", False),
            )

            logger.info("Knowledge agent initialized with native Agno knowledge integration")

        except Exception as exc:
            logger.error("Failed to initialize knowledge agent: %s", exc)
            raise

    async def chat(self, message: str, stream: bool = False) -> str:
        """Process a chat message and return the agent's response.

        Args:
            message: User's message/question
            stream: Whether to stream the response (for future use)

        Returns:
            Agent's response as a string
        """
        if not self.agent:
            return "Error: Agent is not initialized properly."

        try:
            logger.info(f"Processing chat message: {message}")

            # Run the potentially blocking agent.run() in a thread pool
            # to avoid blocking the async event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.agent.run(message, stream=stream)
            )

            # Extract the content from the response
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)

        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def is_ready(self) -> bool:
        """Check if the agent is ready to process requests.

        Returns:
            True if ready, False otherwise
        """
        return self.agent is not None and self.knowledge_manager.is_ready()
