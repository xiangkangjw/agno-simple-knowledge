"""Knowledge planning team with specialized agents for intelligent query handling."""

import os
import logging
from collections.abc import Iterator
from typing import Optional, Dict, Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.db.sqlite import SqliteDb

from agno.utils.log import set_log_level_to_debug, use_agent_logger

from .config import config
from .agno_knowledge import AgnoKnowledgeManager

logger = logging.getLogger(__name__)


class KnowledgePlanningTeam:
    """Intelligent team-based knowledge system with specialized agents."""

    def __init__(self, knowledge_manager: Optional[AgnoKnowledgeManager] = None) -> None:
        """Initialize the knowledge planning team."""
        self.config = config
        self.knowledge_manager = knowledge_manager or AgnoKnowledgeManager()
        self.team: Optional[Team] = None

        if self.config.enable_debug:
            os.environ.setdefault("AGNO_DEBUG", "true")
            use_agent_logger()
            set_log_level_to_debug(source_type="team", level=2)

        self._setup_team()

    def _create_planning_agent(self) -> Agent:
        """Create the planning agent that orchestrates the team."""
        return Agent(
            name="Planning Agent",
            role="Query Analysis and Team Orchestration",
            model=OpenAIChat(
                id=self.config.openai_model,
                api_key=self.config.get_openai_api_key(),
                temperature=0.3,  # Lower temperature for more focused planning
            ),
            instructions="""You are a query planning specialist responsible for analyzing user questions and orchestrating the knowledge team.

Your responsibilities:
1. Analyze the complexity and scope of user queries
2. Determine the best search strategy (simple vs multi-step)
3. Coordinate with specialized team members when needed
4. Ensure efficient use of the knowledge base

For simple, direct questions:
- Handle them directly using knowledge search
- Provide clear, concise answers with sources

For complex, multi-part questions:
- Break them down into logical search steps
- Coordinate with team members for specialized tasks
- Synthesize results into comprehensive responses

Always prioritize efficiency and relevance in knowledge retrieval.""",
            knowledge=self.knowledge_manager.get_knowledge_instance(),
            search_knowledge=True,
            enable_agentic_knowledge_filters=True,
            add_history_to_context=True,
            markdown=True,
        )

    def _create_metadata_agent(self) -> Agent:
        """Create the metadata extraction and filtering agent."""
        return Agent(
            name="Metadata Agent",
            role="Metadata Extraction and Query Optimization",
            model=OpenAIChat(
                id=self.config.openai_model,
                api_key=self.config.get_openai_api_key(),
                temperature=0.2,  # Very focused for metadata extraction
            ),
            instructions="""You are a metadata extraction specialist focused on optimizing knowledge base queries.

Your responsibilities:
1. Analyze user queries to identify relevant metadata filters
2. Extract key terms that can narrow down document searches
3. Suggest optimal search strategies for large knowledge bases
4. Identify document types, topics, and other filtering criteria

When analyzing queries, look for:
- File types mentioned (pdf, markdown, text)
- Topic areas or domains
- Date ranges or temporal references
- Specific projects or directories
- Technical terms that indicate document categories

Provide specific filter recommendations to make knowledge searches more efficient.""",
            knowledge=self.knowledge_manager.get_knowledge_instance(),
            search_knowledge=True,
            enable_agentic_knowledge_filters=True,
            markdown=True,
        )

    def _create_search_agent(self) -> Agent:
        """Create the specialized search execution agent."""
        return Agent(
            name="Search Agent",
            role="Knowledge Base Search Execution",
            model=OpenAIChat(
                id=self.config.openai_model,
                api_key=self.config.get_openai_api_key(),
                temperature=0.4,
            ),
            instructions="""You are a search execution specialist focused on retrieving relevant information from the knowledge base.

Your responsibilities:
1. Execute targeted searches based on planning agent guidance
2. Apply metadata filters for efficient retrieval
3. Evaluate search result quality and relevance
4. Suggest alternative search approaches if initial results are insufficient

Search strategies:
- Use specific filters when provided by the metadata agent
- Start with narrow searches and broaden if needed
- Focus on retrieving the most relevant documents
- Identify gaps in available information

Always provide source citations and explain the search approach used.""",
            knowledge=self.knowledge_manager.get_knowledge_instance(),
            search_knowledge=True,
            enable_agentic_knowledge_filters=True,
            markdown=True,
        )

    def _create_assembly_agent(self) -> Agent:
        """Create the result synthesis and assembly agent."""
        return Agent(
            name="Assembly Agent",
            role="Result Synthesis and Response Assembly",
            model=OpenAIChat(
                id=self.config.openai_model,
                api_key=self.config.get_openai_api_key(),
                temperature=0.6,  # Higher creativity for synthesis
            ),
            instructions="""You are a synthesis specialist responsible for combining multiple search results into coherent, comprehensive responses.

Your responsibilities:
1. Analyze multiple search results and identify key themes
2. Synthesize information from different sources
3. Resolve conflicts or inconsistencies in retrieved information
4. Create well-structured, comprehensive responses
5. Ensure proper attribution and source citations

Response guidelines:
- Organize information logically and clearly
- Highlight the most important findings
- Note any limitations or gaps in available information
- Provide actionable insights when possible
- Maintain source traceability throughout

Always aim for clarity, accuracy, and usefulness in your synthesized responses.""",
            knowledge=self.knowledge_manager.get_knowledge_instance(),
            search_knowledge=True,
            enable_agentic_knowledge_filters=True,
            markdown=True,
        )

    def _setup_team(self) -> None:
        """Set up the knowledge planning team with specialized agents."""
        try:
            knowledge = self.knowledge_manager.get_knowledge_instance()
            if not knowledge:
                raise ValueError("Failed to initialize Agno Knowledge instance")

            # Create specialized agents
            planning_agent = self._create_planning_agent()
            metadata_agent = self._create_metadata_agent()
            search_agent = self._create_search_agent()
            assembly_agent = self._create_assembly_agent()

            # Set up database for team memory (optional)
            db = None
            try:
                db = SqliteDb(db_file="tmp/team_memory.db")
            except Exception as e:
                logger.warning(f"Could not initialize team database: {e}")

            # Create the team with planning agent as leader
            self.team = Team(
                name="Knowledge Planning Team",
                model=OpenAIChat(
                    id=self.config.openai_model,
                    api_key=self.config.get_openai_api_key(),
                    temperature=self.config.temperature,
                ),
                members=[metadata_agent, search_agent, assembly_agent],
                knowledge=knowledge,
                db=db,
                instructions="""You are the leader of an intelligent knowledge team specialized in handling complex document queries.

Team Coordination Guidelines:
1. For simple queries: Handle directly with your knowledge search capabilities
2. For complex queries: Coordinate with team members as follows:
   - Metadata Agent: When you need to optimize search filters
   - Search Agent: For targeted or specialized searches
   - Assembly Agent: When combining multiple search results

Efficiency Principles:
- Start with the simplest approach that will work
- Use team members only when their specialized skills add value
- Avoid unnecessary complexity or redundant searches
- Always prioritize user needs and query intent

Quality Standards:
- Provide accurate, well-sourced information
- Be transparent about limitations or gaps
- Offer actionable insights when possible
- Maintain clear source attribution""",
                search_knowledge=True,
                enable_agentic_knowledge_filters=True,
                add_history_to_context=True,
                show_members_responses=self.config.enable_debug,
                markdown=True,
                debug_mode=self.config.enable_debug,
                debug_level=2 if self.config.enable_debug else 1,
            )
            self.team.initialize_team(debug_mode=self.config.enable_debug)

            logger.info("Knowledge planning team initialized successfully")

        except Exception as exc:
            logger.error("Failed to initialize knowledge planning team: %s", exc)
            raise

    async def chat(self, message: str, stream: bool = False) -> str:
        """Process a chat message using the knowledge planning team."""
        if not self.team:
            return "Error: Knowledge planning team is not initialized properly."

        try:
            logger.info(f"Processing team chat message: {message}")

            # Use the team's run method for coordinated response
            response = self.team.run(
                message,
                stream=stream,
                debug_mode=self.config.enable_debug,
                stream_intermediate_steps=self.config.enable_debug,
            )

            if stream and isinstance(response, Iterator):
                return self._consume_streaming_response(response)

            # Extract the content from the response
            return self._format_run_output(response)

        except Exception as e:
            logger.error(f"Error processing team chat message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def _format_run_output(self, response: Any) -> str:
        """Extract text content from a Team run output."""
        if response is None:
            return ""

        get_content = getattr(response, "get_content_as_string", None)
        if callable(get_content):
            content = get_content()
            if content:
                return content

        content = getattr(response, "content", None)
        if content:
            if isinstance(content, str):
                return content
            return str(content)

        if isinstance(response, str):
            return response

        return ""

    def _consume_streaming_response(self, response: Iterator[Any]) -> str:
        """Consume streamed team events and return the final textual content."""
        final_content: Optional[Any] = None
        text_chunks: list[str] = []

        for event in response:
            content = getattr(event, "content", None)
            if not content:
                continue

            final_content = content
            if isinstance(content, str):
                text_chunks.append(content)

        if isinstance(final_content, str):
            return final_content
        if text_chunks:
            return "".join(text_chunks)
        if final_content is not None:
            return str(final_content)
        return ""

    def is_ready(self) -> bool:
        """Check if the team is ready to process requests."""
        return self.team is not None and self.knowledge_manager.is_ready()

    def refresh_knowledge(self) -> None:
        """Refresh the knowledge base connection after index updates."""
        try:
            self.knowledge_manager.refresh()
            # Re-setup the team with refreshed knowledge
            self._setup_team()
            logger.info("Knowledge planning team refreshed successfully")
        except Exception as e:
            logger.error(f"Failed to refresh knowledge planning team: {e}")

    def get_team_stats(self) -> Dict[str, Any]:
        """Get statistics about the team and its knowledge base."""
        if not self.team:
            return {"status": "Team not initialized"}

        knowledge_stats = self.knowledge_manager.get_knowledge_stats()

        return {
            "status": "Ready",
            "team_name": self.team.name,
            "member_count": len(self.team.members) if hasattr(self.team, 'members') else 0,
            "knowledge_stats": knowledge_stats,
            "capabilities": {
                "agentic_search": True,
                "metadata_filtering": True,
                "team_collaboration": True,
                "conversation_memory": True,
            }
        }
