<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a text-based knowledge management system designed to index and search documents using LlamaIndex, ChromaDB vector storage, and the Agno framework for intelligent reasoning. The project is implemented as a native desktop application using Tauri + React for the frontend and Python for the backend processing.

## Architecture

The system follows a three-layer architecture:

1. **Document Processing Layer**: Python backend with LlamaIndex readers for text, markdown, and PDF files
2. **Storage Layer**: ChromaDB vector store for persistent embeddings  
3. **Interface Layer**: React frontend with Tauri for native desktop integration

Key architectural decisions:
- **Local-first**: All data remains on the user's machine
- **Text-focused**: Prioritizes reliable text extraction and search
- **Manual indexing**: User-controlled refresh for document updates
- **Native desktop UI**: Tauri + React for lightweight distribution
- **Separation of concerns**: Python backend handles document processing, React frontend handles UI

## Current Project Structure

```
src/                     # React frontend
├── App.tsx             # Main application component
├── components/         # UI components
├── lib/               # Utility libraries
├── main.tsx           # React entry point
└── index.css          # Global styles

python-backend/         # Python processing backend
├── api/               # API endpoints
├── core/              # Core processing logic
├── chroma_db/         # ChromaDB storage
├── main.py            # Backend entry point
└── requirements.txt   # Python dependencies

src-tauri/             # Tauri configuration
├── src/               # Rust code
├── tauri.conf.json    # Tauri configuration
└── Cargo.toml         # Rust dependencies

config.yaml            # Directory targets and system settings
package.json           # Node.js dependencies
requirements.txt       # Root Python dependencies
```

## Core Dependencies

### Frontend (React/TypeScript)
- **React 18**: UI framework with TypeScript
- **Tauri**: Native desktop application framework
- **Radix UI**: Component library for consistent UI
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Icon library
- **React Markdown**: Markdown rendering

### Backend (Python)
- **LlamaIndex ecosystem**: llama-index>=0.10.0, llama-index-vector-stores-chroma, llama-index-readers-file, llama-index-embeddings-openai
- **Agno framework**: For intelligent agent reasoning
- **ChromaDB**: Vector storage backend (>=0.4.0)
- **OpenAI**: Embeddings and language model integration
- **FastAPI**: Web framework for backend API

## Development Guidelines

### File Organization
- Keep document processing logic in `python-backend/core/`
- Frontend components in `src/components/`
- API endpoints in `python-backend/api/`
- Use `config.yaml` for user-configurable settings
- Tauri configuration in `src-tauri/tauri.conf.json`

### Key Integration Points
- LlamaIndex handles document reading and chunking in Python backend
- ChromaDB provides persistent vector storage in `python-backend/chroma_db/`
- Agno agent integrates with LlamaIndex query engine for intelligent responses
- Tauri manages communication between React frontend and Python backend
- React components handle user interface and state management

### Implementation Priority
1. ✅ Set up Tauri + React frontend foundation
2. ✅ Set up Python backend with LlamaIndex + ChromaDB
3. ✅ Implement basic document processing for txt, md, pdf
4. 🔄 Create Agno agent with LlamaIndex query engine integration
5. 🔄 Build React chat interface and connect through Tauri commands
6. ⏳ Add configuration management and manual refresh capabilities
7. ⏳ Implement real-time communication between frontend and backend

## Configuration

The system uses multiple configuration files:

### `config.yaml`
- Target directories for document indexing
- OpenAI API configuration
- ChromaDB storage location
- Backend processing settings

### `src-tauri/tauri.conf.json`
- Application window settings
- Build configuration
- Security policies
- Plugin configuration

### `.env` files
- API keys and secrets
- Environment-specific settings
- Database connection strings

## Future Considerations

Post-MVP enhancements may include:
- Menu bar integration for quick access
- Automatic file monitoring for real-time indexing
- Multi-modal document support beyond text


## Openspec

1. Populate your project context:
   "Please read openspec/project.md and help me fill it out
    with details about my project, tech stack, and conventions"

2. Create your first change proposal:
   "I want to add [YOUR FEATURE HERE]. Please create an
    OpenSpec change proposal for this feature"

3. Learn the OpenSpec workflow:
   "Please explain the OpenSpec workflow from openspec/AGENTS.md
    and how I should work with you on this project"