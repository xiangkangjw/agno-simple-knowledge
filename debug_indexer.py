#!/usr/bin/env python3
"""Debug script to test document loading without full backend initialization."""

import sys
import os
import logging
from pathlib import Path

# Add python-backend to the path
sys.path.insert(0, 'python-backend')

# Set up basic logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set minimal environment
os.environ['OPENAI_API_KEY'] = 'sk-test-debug'

try:
    from core.config import config
    from llama_index.core import SimpleDirectoryReader

    logger.info("Testing document discovery...")

    # Test document discovery
    documents_found = []
    for directory in config.target_directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Directory does not exist: {directory}")
            continue

        for ext in config.file_extensions:
            found = list(dir_path.rglob(f"*{ext}"))
            documents_found.extend(found)
            logger.info(f"Found {len(found)} {ext} files in {directory}")

    logger.info(f"Total documents found: {len(documents_found)}")

    # Test loading a small subset (first 3 files)
    test_files = [str(doc) for doc in documents_found[:3]]
    logger.info(f"Testing with first 3 files: {test_files}")

    loaded_docs = []
    for file_path in test_files:
        try:
            logger.info(f"Attempting to load: {file_path}")
            reader = SimpleDirectoryReader(input_files=[file_path])
            docs = reader.load_data()
            loaded_docs.extend(docs)
            logger.info(f"✅ Successfully loaded: {file_path} ({len(docs)} chunks)")
        except Exception as e:
            logger.error(f"❌ Failed to load {file_path}: {e}")

    logger.info(f"Total loaded documents: {len(loaded_docs)}")

except Exception as e:
    logger.error(f"Script failed: {e}")
    import traceback
    traceback.print_exc()