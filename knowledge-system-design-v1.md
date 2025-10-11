# Knowledge System Design - Version 1 (MVP)

## Overview
A simple text-based knowledge management system with indexing and chat capabilities using LlamaIndex, Chroma vector storage, and Agno framework for reasoning.

## Core Technology Choices

### Text Processing Pipeline
- **LlamaIndex** as primary orchestration framework
- **ChromaVectorStore** for persistent vector storage
- **Text embeddings** (OpenAI or sentence-transformers)
- **Manual indexing** with refresh capability

### Chat Interface
- **Agno framework** for agent reasoning
- **LlamaIndex Query Engine** for retrieval and synthesis
- **Tauri + React** for the desktop shell

## Simple Architecture

```
File System → LlamaIndex Readers → Text Nodes → Text Embeddings → ChromaVectorStore
     │               │                   │            │                  │
     │        ┌──────▼──────┐     ┌─────▼─────┐  ┌────▼────┐            │
     │        │PDF Reader   │     │Text Chunks│  │OpenAI   │            │
     │        │Text Reader  │────▶│+ Metadata │─▶│Embedder │            │
     │        │MD Reader    │     └───────────┘  └─────────┘            │
     │        └─────────────┘                                           │
     │                                                                  │
     └─────────────── Agno Agent ◀────── LlamaIndex Query Engine ◀──────┘
                          │                        │
                     Reasoning              Retrieval + Synthesis
```

## Product Design

### MVP Scope
- **Text-only file indexing** (txt, md, pdf text)
- **LlamaIndex document processing** with simple text chunking
- **Basic Agno agent** with LlamaIndex query engine integration
- **Native desktop chat interface** via Tauri + React
- **Configuration file** for target directories
- **Manual refresh** button to re-index

### Key Features
- **Local-first** - all data stays on your machine
- **Text search** - natural language queries over documents
- **Source attribution** - automatic citation with snippets
- **Manual indexing** - refresh button to update index
- **Simple setup** - configuration via YAML file

### Project Structure
```
knowledge-system/
├── src/
│   ├── components/      # React UI components
│   ├── lib/             # Frontend utilities
│   ├── chat_agent.py    # Agno agent wiring used by legacy tooling
│   ├── query_engine.py  # LlamaIndex query processing
│   └── config.py        # Configuration management
├── src-tauri/          # Rust shell and command wiring
├── python-backend/     # FastAPI service and core logic
├── config.yaml         # Directories and settings
└── requirements.txt     # Dependencies
```

## Core Dependencies
```python
# LlamaIndex Core
llama-index>=0.10.0
llama-index-vector-stores-chroma
llama-index-readers-file
llama-index-embeddings-openai

# No additional document processing needed
# (LlamaIndex handles txt, md, pdf natively)

# Chat Interface
agno-framework

# Storage & utilities
chromadb>=0.4.0
openai
python-dotenv
pydantic
```

## Desktop App Shell Choice

Tauri provides the native desktop experience while letting us reuse a modern web UI stack:

- **Lightweight** distribution (~2–3 MB binaries) with system-level integrations
- **Rust** command layer to manage the local FastAPI backend process
- **React + TypeScript** frontend for rapid iteration and polished UI components
- **Shared** configuration with the Python services—no duplicated logic

### Additional Dependencies
```python
# LlamaIndex Core (same as before)
llama-index>=0.10.0
llama-index-vector-stores-chroma
llama-index-readers-file
llama-index-embeddings-openai

# No additional document processing needed
# (LlamaIndex handles txt, md, pdf natively)

# Desktop shell + build tooling handled by package.json / Rust Cargo

# Storage & utilities
chromadb>=0.4.0
openai
python-dotenv
pydantic
```

## System Benefits
- **Privacy**: Everything runs locally
- **Native experience**: Proper macOS integration
- **Simple setup**: Double-click to run
- **Text-focused**: Fast and reliable document search
- **Reasoning**: Agno provides intelligent responses

## Implementation Strategy
1. **Foundation**: Set up LlamaIndex + Chroma indexing
2. **Document processing**: Text extraction from common formats
3. **Chat agent**: Integrate Agno with LlamaIndex query engine
4. **Desktop UI**: Build React interface and integrate through Tauri commands
5. **Polish**: Add file selection, progress indicators, settings

### Future Enhancements (Post-MVP)
- **Menu bar integration** - quick access from system tray
- **File monitoring** - automatic re-indexing of watched folders
- **Multi-modal support** - images and advanced document understanding
