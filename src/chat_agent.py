"""Chat agent using Agno framework with native knowledge integration."""

import logging
from typing import Optional, Dict, Any, List

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.knowledge import KnowledgeTools

from .config import config
from .agno_knowledge import AgnoKnowledgeManager

logger = logging.getLogger(__name__)

class KnowledgeAgent:
    """Main chat agent for the knowledge management system."""

    def __init__(self):
        """Initialize the knowledge agent."""
        self.config = config
        self.knowledge_manager = AgnoKnowledgeManager()
        self.agent: Optional[Agent] = None
        self._setup_agent()
        
    def _setup_agent(self) -> None:
        """Set up the Agno agent with native knowledge integration."""
        try:
            # Get the Agno Knowledge instance
            knowledge = self.knowledge_manager.get_knowledge_instance()
            if not knowledge:
                raise ValueError("Failed to initialize Agno Knowledge instance")

            # Create Knowledge Tools with advanced capabilities
            knowledge_tools = KnowledgeTools(
                knowledge=knowledge,
                think=True,      # Enable reasoning capabilities
                search=True,     # Enable search functionality
                analyze=True,    # Enable analysis capabilities
                add_few_shot=True  # Add few-shot examples for better performance
            )

            # Create the OpenAI model
            model = OpenAIChat(
                id=self.config.openai_model,
                api_key=self.config.get_openai_api_key(),
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            # Create the agent with native knowledge integration and search enabled
            self.agent = Agent(
                model=model,
                knowledge=knowledge,  # Native knowledge integration
                search_knowledge=True,  # Enable knowledge search
                tools=[knowledge_tools],  # Additional tools for think/analyze capabilities
                name="Knowledge Assistant",
                role="Document Search and Q&A Assistant",
                instructions="""You are a helpful knowledge assistant with advanced reasoning capabilities and read-only access to an indexed document database.

Your capabilities:
1. Search through indexed documents with intelligent retrieval
2. Think through complex questions step by step
3. Analyze document content to provide comprehensive answers
4. Provide detailed reasoning for your responses
5. Show relevant sources and explain their relevance

Important limitations:
- You have READ-ONLY access to the knowledge base
- You cannot add, update, or delete documents
- Document indexing is handled by a separate system

When users ask questions:
- ALWAYS use your knowledge tools to search the indexed documents first
- Use the think tool to reason through complex questions step by step
- Use the analyze tool to provide deeper insights from the content
- Provide comprehensive, well-reasoned answers based on indexed content
- Always cite your sources and explain how they support your answer
- If information is incomplete, clearly state what's missing
- If users want to add documents, direct them to use the indexer system

Guidelines:
- Be thorough and analytical in your responses
- Distinguish between information from documents vs. general knowledge
- Explain your reasoning process when helpful
- Provide actionable insights when possible
- Remind users about read-only limitations when relevant""",
                markdown=True,
                show_tool_calls=True,
                debug_mode=self.config.get('system.enable_debug', False)
            )

            logger.info("Knowledge agent initialized successfully with native Agno integration")

        except Exception as e:
            logger.error(f"Failed to initialize knowledge agent: {e}")
            raise
    
    def chat(self, message: str, stream: bool = False) -> str:
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
            
            # Get response from the agent
            response = self.agent.run(message, stream=stream)
            
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
    
    def add_documents(self, file_paths: List[str]) -> str:
        """Add new documents to the knowledge base.

        Note: This agent only provides read-only access. Use the indexer to add documents.

        Args:
            file_paths: List of file paths to add

        Returns:
            Status message directing to use indexer
        """
        return "This agent has read-only access to the knowledge base. To add documents, use the DocumentIndexer from the indexer module."
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats.
        
        Returns:
            List of supported file extensions
        """
        return self.config.file_extensions
    
    def get_target_directories(self) -> List[str]:
        """Get list of target directories for indexing.
        
        Returns:
            List of target directory paths
        """
        return self.config.target_directories
    
    def is_ready(self) -> bool:
        """Check if the agent is ready to process requests.

        Returns:
            True if ready, False otherwise
        """
        return self.agent is not None and self.knowledge_manager.is_ready()

    def refresh_knowledge(self) -> str:
        """Refresh the knowledge base from target directories.

        Note: This agent has read-only access. Use the indexer to refresh documents.

        Returns:
            Status message directing to use indexer
        """
        return "This agent has read-only access to the knowledge base. To refresh documents, use the DocumentIndexer.refresh_index() method."

    def get_knowledge_stats(self) -> str:
        """Get statistics about the current knowledge base connection.

        Returns:
            Formatted string with knowledge statistics
        """
        try:
            stats = self.knowledge_manager.get_knowledge_stats()
            result = f"""**Knowledge Base Connection:**
- Status: {stats.get('status', 'Unknown')}
- Storage path: {stats.get('storage_path', 'Not specified')}
- Collection: {stats.get('collection_name', 'Not specified')}"""

            if 'note' in stats:
                result += f"\n- Note: {stats['note']}"

            return result
        except Exception as e:
            return f"Error getting knowledge stats: {str(e)}"
