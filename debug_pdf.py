#!/usr/bin/env python3
"""Debug script to test PDF loading specifically."""

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

    # Find PDF files
    pdf_files = []
    for directory in config.target_directories:
        dir_path = Path(directory)
        if dir_path.exists():
            pdf_files.extend(list(dir_path.rglob("*.pdf")))

    logger.info(f"Found {len(pdf_files)} PDF files")

    # Test loading first PDF
    if pdf_files:
        test_pdf = str(pdf_files[0])
        logger.info(f"Testing PDF: {test_pdf}")

        try:
            reader = SimpleDirectoryReader(input_files=[test_pdf])
            docs = reader.load_data()
            logger.info(f"✅ Successfully loaded PDF: {len(docs)} chunks")
        except Exception as e:
            logger.error(f"❌ Failed to load PDF: {e}")
            import traceback
            traceback.print_exc()

except Exception as e:
    logger.error(f"Script failed: {e}")
    import traceback
    traceback.print_exc()