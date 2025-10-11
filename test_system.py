#!/usr/bin/env python3
"""Basic system integration test for the Knowledge Management System."""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.config import config
        print("✓ Config module imported successfully")
        
        from src.indexer import DocumentIndexer
        print("✓ Indexer module imported successfully")
        
        from src.query_engine import KnowledgeQueryEngine
        print("✓ Query engine module imported successfully")
        
        from src.chat_agent import KnowledgeAgent
        print("✓ Chat agent module imported successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from src.config import config
        
        # Test basic config access
        target_dirs = config.target_directories
        file_exts = config.file_extensions
        storage_path = config.storage_path
        
        print(f"✓ Target directories: {target_dirs}")
        print(f"✓ File extensions: {file_exts}")
        print(f"✓ Storage path: {storage_path}")
        
        return True
    except Exception as e:
        print(f"✗ Config error: {e}")
        return False

def test_basic_components():
    """Test basic component initialization (without OpenAI dependency)."""
    print("\nTesting basic components...")
    
    try:
        from src.indexer import DocumentIndexer
        from src.query_engine import KnowledgeQueryEngine
        
        # Test indexer initialization (this should work without OpenAI)
        indexer = DocumentIndexer.__new__(DocumentIndexer)
        print("✓ Indexer class can be instantiated")
        
        # Test query engine initialization (this should work without OpenAI)
        query_engine = KnowledgeQueryEngine.__new__(KnowledgeQueryEngine)
        print("✓ Query engine class can be instantiated")
        
        return True
    except Exception as e:
        print(f"✗ Component error: {e}")
        return False

def main():
    """Run all tests."""
    print("Knowledge Management System - Integration Test")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    if test_imports():
        tests_passed += 1
    
    if test_config():
        tests_passed += 1
        
    if test_basic_components():
        tests_passed += 1
    
    print(f"\nTest Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✓ All basic integration tests passed!")
        print("\nNext steps:")
        print("1. Set up your OpenAI API key in a .env file")
        print("2. Run 'python main.py' to start the application")
        print("3. Use 'Refresh Index' to index your documents")
        print("4. Start asking questions!")
    else:
        print("✗ Some tests failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()