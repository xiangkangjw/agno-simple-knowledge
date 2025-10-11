"""Query engine for processing natural language queries against the document index."""

import logging
from typing import Optional, Dict, Any, List

from llama_index.core import get_response_synthesizer
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.llms.openai import OpenAI

from .config import config
from .indexer import DocumentIndexer

logger = logging.getLogger(__name__)

class KnowledgeQueryEngine:
    """Query engine for natural language document search and retrieval."""
    
    def __init__(self, indexer: Optional[DocumentIndexer] = None):
        """Initialize the query engine.
        
        Args:
            indexer: Optional DocumentIndexer instance. If None, creates a new one.
        """
        self.config = config
        self.indexer = indexer or DocumentIndexer()
        self.query_engine: Optional[RetrieverQueryEngine] = None
        self._setup_llm()
        
    def _setup_llm(self) -> None:
        """Configure the language model for query processing."""
        self.llm = OpenAI(
            model=self.config.openai_model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            api_key=self.config.get_openai_api_key()
        )
        
    def initialize(self) -> None:
        """Initialize the query engine with the document index."""
        # Get or create the index
        index = self.indexer.get_or_create_index()
        
        # Create retriever
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=self.config.max_results,
        )
        
        # Create response synthesizer
        response_synthesizer = get_response_synthesizer(
            llm=self.llm,
            response_mode="tree_summarize",
        )
        
        # Create post-processor to filter by similarity
        similarity_postprocessor = SimilarityPostprocessor(similarity_cutoff=0.6)
        
        # Create query engine
        self.query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer,
            node_postprocessors=[similarity_postprocessor]
        )
        
        logger.info("Query engine initialized successfully")
        
    def query(self, question: str) -> Optional[Dict[str, Any]]:
        """Process a natural language query against the document index.
        
        Args:
            question: Natural language question to ask
            
        Returns:
            Dictionary containing the response and metadata, or None if error
        """
        if self.query_engine is None:
            logger.error("Query engine not initialized. Call initialize() first.")
            return None
            
        try:
            logger.info(f"Processing query: {question}")
            
            # Execute the query
            response = self.query_engine.query(question)
            
            # Extract source documents
            source_nodes = response.source_nodes if hasattr(response, 'source_nodes') else []
            sources = []
            
            for node in source_nodes:
                source_info = {
                    "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                    "score": getattr(node, 'score', None),
                    "metadata": node.metadata if hasattr(node, 'metadata') else {}
                }
                sources.append(source_info)
            
            result = {
                "answer": str(response),
                "sources": sources,
                "query": question,
                "metadata": {
                    "response_type": type(response).__name__,
                    "source_count": len(sources)
                }
            }
            
            logger.info(f"Query processed successfully. Found {len(sources)} sources.")
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": f"Sorry, I encountered an error processing your query: {str(e)}",
                "sources": [],
                "query": question,
                "metadata": {"error": str(e)}
            }
    
    def search_documents(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for documents similar to the query without generating an answer.
        
        Args:
            query: Search query
            top_k: Number of top results to return (uses config default if None)
            
        Returns:
            List of matching documents with metadata
        """
        if self.query_engine is None:
            logger.error("Query engine not initialized. Call initialize() first.")
            return []
            
        try:
            # Use the retriever directly for document search
            retriever = self.query_engine.retriever
            if top_k:
                retriever.similarity_top_k = top_k
                
            nodes = retriever.retrieve(query)
            
            results = []
            for node in nodes:
                result = {
                    "text": node.text,
                    "score": getattr(node, 'score', None),
                    "metadata": node.metadata if hasattr(node, 'metadata') else {},
                    "node_id": node.node_id if hasattr(node, 'node_id') else None
                }
                results.append(result)
                
            logger.info(f"Document search completed. Found {len(results)} matches.")
            return results
            
        except Exception as e:
            logger.error(f"Error in document search: {e}")
            return []
    
    def refresh_index(self) -> bool:
        """Refresh the underlying document index.
        
        Returns:
            True if refresh was successful, False otherwise
        """
        try:
            logger.info("Refreshing document index...")
            self.indexer.refresh_index()
            
            # Reinitialize the query engine with the new index
            self.initialize()
            
            logger.info("Index refresh completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing index: {e}")
            return False
    
    def add_documents(self, file_paths: List[str]) -> bool:
        """Add new documents to the index.
        
        Args:
            file_paths: List of file paths to add
            
        Returns:
            True if documents were added successfully, False otherwise
        """
        try:
            logger.info(f"Adding {len(file_paths)} documents to index...")
            self.indexer.add_documents(file_paths)
            
            # Reinitialize the query engine to pick up new documents
            self.initialize()
            
            logger.info("Documents added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index.
        
        Returns:
            Dictionary with index statistics
        """
        return self.indexer.get_index_stats()
    
    def is_ready(self) -> bool:
        """Check if the query engine is ready to process queries.
        
        Returns:
            True if ready, False otherwise
        """
        return self.query_engine is not None
