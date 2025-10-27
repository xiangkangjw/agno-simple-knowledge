"""Document indexing system using LlamaIndex and ChromaDB."""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import time

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.readers.file import PyMuPDFReader
import chromadb

from .config import config

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """Handles document loading, processing, and indexing with LlamaIndex and ChromaDB."""

    # Error category constants
    PDF_ERROR_CATEGORIES = {
        'corrupted': 'File integrity issue',
        'encrypted': 'Password-protected PDF',
        'empty': 'No extractable text',
        'oversized': 'Exceeds size limit',
        'parse_error': 'PDF parsing failed',
        'timeout': 'Processing timeout',
        'permission': 'Access denied',
        'invalid': 'Not a valid PDF',
    }

    def __init__(self):
        """Initialize the document indexer."""
        self.config = config

        # Initialize PDF reader placeholder
        self._pdf_reader: Optional[PyMuPDFReader] = None

        # Tracking for PDF processing statistics
        self._pdf_stats: Dict[str, Any] = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'errors_by_category': {cat: 0 for cat in self.PDF_ERROR_CATEGORIES},
            'failed_files': [],  # List of (filename, error_category, error_message)
            'total_processing_time': 0.0,
        }

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

        # Initialize PDF reader if enabled
        if self.config.pdf_enabled:
            self._pdf_reader = PyMuPDFReader()
            logger.info("PyMuPDFReader initialized for PDF processing")

    def _validate_pdf(self, file_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate PDF file before processing.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (is_valid, error_category, error_message)
        """
        path = Path(file_path)

        # Check file exists and is readable
        if not path.exists():
            return False, 'invalid', 'File does not exist'

        if not path.is_file():
            return False, 'invalid', 'Not a file'

        try:
            # Check file permissions
            if not os.access(path, os.R_OK):
                return False, 'permission', 'File is not readable'

            # Check file size
            file_size_mb = path.stat().st_size / (1024 * 1024)
            max_size = self.config.pdf_max_file_size_mb
            if file_size_mb > max_size:
                return False, 'oversized', f'File size {file_size_mb:.1f}MB exceeds limit {max_size}MB'

            # Check if it's a PDF (magic bytes check)
            with open(path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False, 'invalid', 'Not a valid PDF file (invalid header)'

            # Check if PDF is encrypted (basic check)
            if self.config.pdf_skip_encrypted:
                try:
                    import fitz
                    pdf_doc = fitz.open(path)
                    if pdf_doc.is_pdf and pdf_doc.needs_pass:
                        pdf_doc.close()
                        return False, 'encrypted', 'PDF is password-protected'
                    pdf_doc.close()
                except Exception as e:
                    logger.warning(f"Could not check if PDF is encrypted: {e}")
                    # Continue anyway, let the parser handle it

            return True, None, None

        except OSError as e:
            return False, 'permission', f'Cannot access file: {str(e)}'
        except Exception as e:
            return False, 'corrupted', f'Validation error: {str(e)}'

    def _track_pdf_error(self, file_path: str, error_category: str, error_message: str) -> None:
        """Track a PDF processing error.

        Args:
            file_path: Path to the PDF file
            error_category: Category of error
            error_message: Detailed error message
        """
        filename = Path(file_path).name
        self._pdf_stats['failed'] += 1
        self._pdf_stats['errors_by_category'][error_category] = (
            self._pdf_stats['errors_by_category'].get(error_category, 0) + 1
        )
        self._pdf_stats['failed_files'].append({
            'filename': filename,
            'path': file_path,
            'error_category': error_category,
            'error_message': error_message
        })
        logger.warning(f"PDF error [{error_category}] {filename}: {error_message}")

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
        """Load documents using LlamaIndex readers with PDF-specific handling.

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

        # Reset PDF stats for this load operation
        self._pdf_stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'errors_by_category': {cat: 0 for cat in self.PDF_ERROR_CATEGORIES},
            'failed_files': [],
            'total_processing_time': 0.0,
        }

        documents = []
        pdf_files = [f for f in file_paths if f.lower().endswith('.pdf')]
        non_pdf_files = [f for f in file_paths if not f.lower().endswith('.pdf')]

        # Track PDF statistics
        self._pdf_stats['total'] = len(pdf_files)

        # Load PDFs with enhanced error handling
        for file_path in pdf_files:
            start_time = time.time()
            try:
                # Validate PDF before processing
                is_valid, error_cat, error_msg = self._validate_pdf(file_path)
                if not is_valid:
                    self._track_pdf_error(file_path, error_cat, error_msg)
                    continue

                # Load PDF using PyMuPDFReader
                if self._pdf_reader is None:
                    logger.error(f"PDF reader not initialized, skipping: {file_path}")
                    self._track_pdf_error(file_path, 'parse_error', 'PDF reader not initialized')
                    continue

                docs = self._pdf_reader.load_data(
                    file_path=Path(file_path),
                    metadata=self.config.pdf_extract_metadata
                )

                if not docs:
                    self._track_pdf_error(file_path, 'empty', 'No text extracted from PDF')
                    continue

                documents.extend(docs)
                self._pdf_stats['successful'] += 1
                elapsed = time.time() - start_time
                self._pdf_stats['total_processing_time'] += elapsed
                logger.info(f"✓ Loaded PDF {Path(file_path).name} ({len(docs)} pages, {elapsed:.2f}s)")

            except TimeoutError:
                self._track_pdf_error(file_path, 'timeout', 'Processing timeout exceeded')
            except PermissionError:
                self._track_pdf_error(file_path, 'permission', 'Permission denied')
            except Exception as e:
                error_msg = str(e)
                # Try to categorize the error
                if 'encrypt' in error_msg.lower() or 'password' in error_msg.lower():
                    error_cat = 'encrypted'
                elif 'corrupt' in error_msg.lower():
                    error_cat = 'corrupted'
                else:
                    error_cat = 'parse_error'
                self._track_pdf_error(file_path, error_cat, error_msg)

        # Load non-PDF files with generic reader
        for file_path in non_pdf_files:
            try:
                reader = SimpleDirectoryReader(input_files=[file_path])
                docs = reader.load_data()
                documents.extend(docs)
                logger.debug(f"Loaded: {file_path}")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        logger.info(
            f"Successfully loaded {len(documents)} documents "
            f"(PDFs: {self._pdf_stats['successful']}/{self._pdf_stats['total']} successful)"
        )
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

    def _get_unique_source_files(self) -> int:
        """Count unique source files in the ChromaDB collection.

        Returns:
            Number of unique source files indexed
        """
        try:
            # Get all documents from the collection
            all_docs = self.chroma_collection.get()

            if not all_docs or not all_docs.get('metadatas'):
                return 0

            # Extract unique file paths from metadata
            source_files = set()
            for metadata in all_docs['metadatas']:
                if metadata and 'file_path' in metadata:
                    source_files.add(metadata['file_path'])

            return len(source_files)
        except Exception as e:
            logger.warning(f"Could not count unique source files: {e}")
            return 0

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index including PDF processing metrics.

        Returns:
            Dictionary with index statistics and PDF metrics
        """
        stats = {}

        # Always add PDF statistics if available
        if self._pdf_stats['total'] > 0:
            stats['pdf_processing'] = {
                'total_files': self._pdf_stats['total'],
                'successful': self._pdf_stats['successful'],
                'failed': self._pdf_stats['failed'],
                'success_rate': f"{(self._pdf_stats['successful'] / self._pdf_stats['total'] * 100):.1f}%" if self._pdf_stats['total'] > 0 else "N/A",
                'total_processing_time_seconds': f"{self._pdf_stats['total_processing_time']:.2f}",
                'errors_by_category': {
                    cat: count
                    for cat, count in self._pdf_stats['errors_by_category'].items()
                    if count > 0
                },
            }

            # Include failed files list if there are failures
            if self._pdf_stats['failed_files']:
                stats['pdf_processing']['failed_files'] = self._pdf_stats['failed_files'][:10]  # Show first 10 failures
                if len(self._pdf_stats['failed_files']) > 10:
                    stats['pdf_processing']['failed_files'].append({
                        'filename': f"... and {len(self._pdf_stats['failed_files']) - 10} more"
                    })

        if self.index is None:
            stats.update({"status": "No index loaded", "document_count": 0, "source_file_count": 0})
            return stats

        try:
            doc_count = self.chroma_collection.count()
            source_file_count = self._get_unique_source_files()
            stats.update({
                "status": "Index loaded",
                "document_count": doc_count,
                "source_file_count": source_file_count,
                "storage_path": self.config.storage_path,
                "collection_name": self.collection_name
            })

            return stats
        except Exception as e:
            stats.update({"status": f"Error getting stats: {e}", "document_count": 0, "source_file_count": 0})
            return stats
