"""Document indexing system using LlamaIndex and ChromaDB."""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
import chromadb

from .config import config

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """Handles document loading, processing, and indexing with LlamaIndex and ChromaDB."""

    def __init__(self):
        """Initialize the document indexer."""
        self.config = config
        self._setup_settings()
        self._initialize_chroma()
        self.index: Optional[VectorStoreIndex] = None

    def _setup_settings(self) -> None:
        """Configure LlamaIndex global settings."""
        # Set up OpenAI embedding
        Settings.embed_model = OpenAIEmbedding(
            model=self.config.embedding_model,
            api_key=self.config.get_openai_api_key()
        )

        # Set up text splitter
        Settings.node_parser = SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )

    def _initialize_chroma(self) -> None:
        """Initialize ChromaDB client and collection."""
        # Create storage directory if it doesn't exist
        storage_path = Path(self.config.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=str(storage_path))

        # Get or create collection
        self.collection_name = self.config.collection_name
        try:
            self.chroma_collection = self.chroma_client.get_collection(self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except:
            self.chroma_collection = self.chroma_client.create_collection(self.collection_name)
            logger.info(f"Created new collection: {self.collection_name}")

        # Create ChromaVectorStore
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)

    def _get_documents_from_directories(self) -> List[str]:
        """Get all supported documents from target directories."""
        documents = []

        for directory in self.config.target_directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                logger.warning(f"Directory does not exist: {directory}")
                continue

            for ext in self.config.file_extensions:
                documents.extend(dir_path.rglob(f"*{ext}"))

        return [str(doc) for doc in documents]

    def load_documents(self, file_paths: Optional[List[str]] = None) -> List[Any]:
        """Load documents using LlamaIndex readers.

        Args:
            file_paths: Optional list of specific file paths to load.
                       If None, loads all documents from target directories.

        Returns:
            List of loaded documents
        """
        if file_paths is None:
            file_paths = self._get_documents_from_directories()

        if not file_paths:
            logger.warning("No documents found to load")
            return []

        logger.info(f"Loading {len(file_paths)} documents...")

        # Use SimpleDirectoryReader with specific files
        documents = []
        for file_path in file_paths:
            try:
                # Load each file individually to handle errors gracefully
                reader = SimpleDirectoryReader(input_files=[file_path])
                docs = reader.load_data()
                documents.extend(docs)
                logger.debug(f"Loaded: {file_path}")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        logger.info(f"Successfully loaded {len(documents)} documents")
        return documents

    def create_index(self, documents: Optional[List[Any]] = None) -> VectorStoreIndex:
        """Create or update the vector index.

        Args:
            documents: Optional list of documents to index.
                      If None, loads documents from target directories.

        Returns:
            The created or updated VectorStoreIndex
        """
        if documents is None:
            documents = self.load_documents()

        if not documents:
            raise ValueError("No documents available for indexing")

        # Create storage context with ChromaDB
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

        # Create the index
        logger.info("Creating vector index...")
        self.index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context
        )

        logger.info(f"Index created with {len(documents)} documents")
        return self.index

    def load_existing_index(self) -> Optional[VectorStoreIndex]:
        """Load existing index from ChromaDB storage.

        Returns:
            Loaded VectorStoreIndex or None if no existing index
        """
        try:
            # Check if collection has any documents
            if self.chroma_collection.count() == 0:
                logger.info("No existing documents in ChromaDB collection")
                return None

            # Create storage context and load index
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                storage_context=storage_context
            )

            logger.info(f"Loaded existing index with {self.chroma_collection.count()} documents")
            return self.index

        except Exception as e:
            logger.error(f"Failed to load existing index: {e}")
            return None

    def get_or_create_index(self) -> VectorStoreIndex:
        """Get existing index or create a new one.

        Returns:
            VectorStoreIndex ready for querying
        """
        # Try to load existing index first
        existing_index = self.load_existing_index()
        if existing_index is not None:
            return existing_index

        # Create new index if none exists
        logger.info("No existing index found, creating new index...")
        return self.create_index()

    def add_documents(self, file_paths: List[str]) -> None:
        """Add new documents to the existing index.

        Args:
            file_paths: List of file paths to add
        """
        if self.index is None:
            self.index = self.get_or_create_index()

        documents = self.load_documents(file_paths)
        if documents:
            logger.info(f"Adding {len(documents)} documents to existing index...")

            for doc in documents:
                self.index.insert(doc)

            logger.info("Documents added successfully")

    def refresh_index(self) -> VectorStoreIndex:
        """Refresh the entire index by rebuilding from target directories.

        Returns:
            Newly created VectorStoreIndex
        """
        logger.info("Refreshing index...")

        # Clear existing collection
        try:
            self.chroma_client.delete_collection(self.collection_name)
            logger.info("Cleared existing collection")
        except:
            pass  # Collection might not exist

        # Recreate collection and vector store
        self.chroma_collection = self.chroma_client.create_collection(self.collection_name)
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)

        # Create new index
        return self.create_index()

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index.

        Returns:
            Dictionary with index statistics
        """
        if self.index is None:
            return {"status": "No index loaded", "document_count": 0}

        try:
            doc_count = self.chroma_collection.count()
            return {
                "status": "Index loaded",
                "document_count": doc_count,
                "storage_path": self.config.storage_path,
                "collection_name": self.collection_name
            }
        except Exception as e:
            return {"status": f"Error getting stats: {e}", "document_count": 0}
