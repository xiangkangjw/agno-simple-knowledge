# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a text-based knowledge management system designed to index and search documents using LlamaIndex, ChromaDB vector storage, and the Agno framework for intelligent reasoning. The project aims to create a native macOS application for local document search and chat capabilities.

## Architecture

The system follows a three-layer architecture:

1. **Document Processing Layer**: LlamaIndex readers for text, markdown, and PDF files
2. **Storage Layer**: ChromaDB vector store for persistent embeddings  
3. **Interface Layer**: Agno agent with LlamaIndex query engine for natural language interaction

Key architectural decisions:
- **Local-first**: All data remains on the user's machine
- **Text-focused**: Prioritizes reliable text extraction and search
- **Manual indexing**: User-controlled refresh for document updates
- **Native macOS UI**: PyQt6 for better system integration

## Planned Project Structure

```
src/
├── indexer.py       # Document loading and indexing with LlamaIndex
├── chat_agent.py    # Agno agent with LlamaIndex query engine
├── query_engine.py  # LlamaIndex query processing and retrieval
└── config.py        # Configuration management

ui/
└── macos_app.py     # PyQt6 native macOS application

config.yaml          # Directory targets and system settings
requirements.txt     # Python dependencies
```

## Core Dependencies

- **LlamaIndex ecosystem**: llama-index>=0.10.0, llama-index-vector-stores-chroma, llama-index-readers-file, llama-index-embeddings-openai
- **Agno framework**: For intelligent agent reasoning
- **ChromaDB**: Vector storage backend (>=0.4.0)
- **PyQt6**: Native macOS interface
- **OpenAI**: Embeddings and language model integration

## Development Guidelines

### File Organization
- Keep document processing logic in `src/indexer.py`
- Isolate agent reasoning in `src/chat_agent.py` using Agno patterns
- Separate UI concerns in `ui/macos_app.py`
- Use `config.yaml` for user-configurable settings

### Key Integration Points
- LlamaIndex handles document reading and chunking natively
- ChromaDB provides persistent vector storage between sessions
- Agno agent integrates with LlamaIndex query engine for intelligent responses
- PyQt6 provides native macOS look and feel

### Implementation Priority
1. Set up LlamaIndex + ChromaDB indexing foundation
2. Implement basic document processing for txt, md, pdf
3. Create Agno agent with LlamaIndex query engine integration
4. Build PyQt6 chat interface with file selection
5. Add configuration management and manual refresh capabilities

## Configuration

The system uses `config.yaml` for:
- Target directories for document indexing
- OpenAI API configuration
- ChromaDB storage location
- UI preferences and settings

## Future Considerations

Post-MVP enhancements may include:
- Menu bar integration for quick access
- Automatic file monitoring for real-time indexing
- Multi-modal document support beyond text