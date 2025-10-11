#!/usr/bin/env python3
"""Debug script to inspect ChromaDB vector store contents."""

import sys
import os
from pathlib import Path
import json

# Add python-backend to the path
sys.path.insert(0, 'python-backend')

try:
    from core.config import config
    import chromadb

    print("=== ChromaDB Vector Store Inspector ===\n")

    # Initialize ChromaDB client
    storage_path = Path(config.storage_path)
    print(f"Storage path: {storage_path}")

    if not storage_path.exists():
        print("❌ Storage path doesn't exist yet - no documents indexed")
        sys.exit(0)

    client = chromadb.PersistentClient(path=str(storage_path))

    # List all collections
    collections = client.list_collections()
    print(f"Collections found: {len(collections)}")
    for col in collections:
        print(f"  - {col.name}")

    # Focus on knowledge_base collection
    try:
        collection = client.get_collection("knowledge_base")
        print(f"\n=== Knowledge Base Collection ===")
        print(f"Document count: {collection.count()}")

        if collection.count() > 0:
            # Get first few documents for inspection
            limit = min(5, collection.count())
            results = collection.get(
                limit=limit,
                include=["documents", "metadatas"]
            )

            print(f"\n=== Sample Documents (first {limit}) ===")
            for i, (doc_id, doc, metadata) in enumerate(zip(
                results["ids"],
                results["documents"],
                results["metadatas"]
            )):
                print(f"\n--- Document {i+1} ---")
                print(f"ID: {doc_id}")
                print(f"Metadata: {json.dumps(metadata, indent=2)}")
                print(f"Content preview: {doc[:200]}...")
                if len(doc) > 200:
                    print(f"[Content truncated - full length: {len(doc)} chars]")

    except Exception as e:
        print(f"❌ Error accessing knowledge_base collection: {e}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the project root and dependencies are installed")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()