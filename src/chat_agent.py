"""Chat agent using Agno framework with LlamaIndex integration."""

import logging
from typing import Optional, Dict, Any, List

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import Toolkit

from .config import config
from .query_engine import KnowledgeQueryEngine

logger = logging.getLogger(__name__)

class DocumentSearchTool(Toolkit):
    """Custom tool for searching documents using the knowledge query engine."""
    
    def __init__(self, query_engine: KnowledgeQueryEngine):
        super().__init__()
        self.query_engine = query_engine
        
    def search_documents(self, query: str) -> str:
        """Search through indexed documents for relevant information.
        
        Args:
            query: The search query or question
            
        Returns:
            Formatted response with answer and sources
        """
        if not self.query_engine.is_ready():
            return "Error: Knowledge base is not initialized. Please index some documents first."
            
        try:
            result = self.query_engine.query(query)
            if not result:
                return "Sorry, I couldn't process your query. Please try again."
                
            answer = result.get("answer", "No answer available")
            sources = result.get("sources", [])
            
            # Format the response with sources
            response = f"**Answer:** {answer}\n\n"
            
            if sources:
                response += "**Sources:**\n"
                for i, source in enumerate(sources[:3], 1):  # Limit to top 3 sources
                    text_preview = source.get("text", "")[:100] + "..."
                    metadata = source.get("metadata", {})
                    file_path = metadata.get("file_path", "Unknown source")
                    score = source.get("score")
                    
                    response += f"{i}. {file_path}"
                    if score:
                        response += f" (relevance: {score:.2f})"
                    response += f"\n   Preview: {text_preview}\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in document search: {e}")
            return f"Sorry, I encountered an error while searching: {str(e)}"
    
    def get_index_stats(self) -> str:
        """Get statistics about the current document index.
        
        Returns:
            Formatted string with index statistics
        """
        try:
            stats = self.query_engine.get_index_stats()
            return f"""**Document Index Statistics:**
- Status: {stats.get('status', 'Unknown')}
- Document count: {stats.get('document_count', 0)}
- Storage path: {stats.get('storage_path', 'Not specified')}
- Collection: {stats.get('collection_name', 'Not specified')}"""
        except Exception as e:
            return f"Error getting index stats: {str(e)}"
    
    def refresh_index(self) -> str:
        """Refresh the document index by rebuilding from target directories.
        
        Returns:
            Status message about the refresh operation
        """
        try:
            success = self.query_engine.refresh_index()
            if success:
                stats = self.query_engine.get_index_stats()
                return f"Index refreshed successfully! Now indexing {stats.get('document_count', 0)} documents."
            else:
                return "Failed to refresh index. Please check the logs for details."
        except Exception as e:
            return f"Error refreshing index: {str(e)}"

class KnowledgeAgent:
    """Main chat agent for the knowledge management system."""
    
    def __init__(self):
        """Initialize the knowledge agent."""
        self.config = config
        self.query_engine = KnowledgeQueryEngine()
        self.agent: Optional[Agent] = None
        self._setup_agent()
        
    def _setup_agent(self) -> None:
        """Set up the Agno agent with tools and configuration."""
        try:
            # Initialize the query engine
            self.query_engine.initialize()
            
            # Create the document search tool
            search_tool = DocumentSearchTool(self.query_engine)
            
            # Create the OpenAI model
            model = OpenAIChat(
                id=self.config.openai_model,
                api_key=self.config.get_openai_api_key(),
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            # Create the agent
            self.agent = Agent(
                model=model,
                tools=[search_tool],
                name="Knowledge Assistant",
                role="Document Search and Q&A Assistant",
                instructions="""You are a helpful knowledge assistant that can search through indexed documents to answer questions.

Your capabilities:
1. Search through indexed documents using the search_documents tool
2. Provide detailed answers based on the document content
3. Show relevant sources for your answers
4. Get statistics about the document index
5. Refresh the document index when needed

When users ask questions:
- Use the search_documents tool to find relevant information
- Provide comprehensive answers based on the search results
- Always mention your sources when possible
- If you can't find relevant information, suggest they might need to index more documents

Guidelines:
- Be helpful and informative
- Clearly distinguish between information from the documents vs. your general knowledge
- Suggest using refresh_index if users mention new documents
- Use get_index_stats to help users understand what's currently indexed""",
                markdown=True,
                show_tool_calls=True,
                debug_mode=self.config.get('system.enable_debug', False)
            )
            
            logger.info("Knowledge agent initialized successfully")
            
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
        
        Args:
            file_paths: List of file paths to add
            
        Returns:
            Status message
        """
        try:
            success = self.query_engine.add_documents(file_paths)
            if success:
                return f"Successfully added {len(file_paths)} documents to the knowledge base."
            else:
                return "Failed to add documents. Please check the logs for details."
        except Exception as e:
            return f"Error adding documents: {str(e)}"
    
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
        return self.agent is not None and self.query_engine.is_ready()
