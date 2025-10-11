# Knowledge Management System

A local document search and chat system that keeps all your data private while providing intelligent document search capabilities.

## Features

- **Local-first**: All data remains on your machine
- **Intelligent Search**: Vector-based document search with natural language queries
- **Chat Interface**: Ask questions about your documents in natural language
- **Native macOS UI**: Clean, native interface built with PyQt6
- **Multiple Formats**: Supports text, markdown, and PDF files
- **Privacy Focused**: No data sent to external services except OpenAI for embeddings/chat

## Architecture

- **Document Processing**: LlamaIndex for text extraction and chunking
- **Vector Storage**: ChromaDB for persistent embeddings
- **AI Agent**: Agno framework for intelligent reasoning
- **Interface**: PyQt6 for native macOS experience

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agno-simple-knowledge
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

4. **Configure target directories** (optional)
   Edit `config.yaml` to specify which directories to scan for documents.

## Usage

### Running the Application

```bash
python main.py
```

### First Time Setup

1. Launch the application
2. Click "Refresh Index" to scan and index documents from your configured directories
3. Or use "Add Documents" / "Add Folder" to manually add specific files
4. Start asking questions in the chat interface!

### Example Queries

- "What documents do I have about machine learning?"
- "Summarize the main points from my meeting notes"
- "Find information about Python programming"
- "What are the key takeaways from my research papers?"

## Configuration

Edit `config.yaml` to customize:

- **Target directories**: Where to look for documents
- **File types**: Which file extensions to index
- **OpenAI settings**: Model and parameter configurations
- **UI preferences**: Window size, themes, etc.

## Supported File Types

- Text files (`.txt`)
- Markdown files (`.md`)
- PDF files (`.pdf`)

## Privacy

- All document processing happens locally
- Only API calls to OpenAI for embeddings and chat responses
- No document content sent to external services
- Vector embeddings stored locally in ChromaDB

## Troubleshooting

### Common Issues

1. **"Agent not initialized"**: Make sure you have a valid OpenAI API key in your `.env` file

2. **"No documents found"**: Check that your target directories contain supported file types

3. **Slow indexing**: Large documents or many files will take time to process initially

4. **Import errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`

### Logs

The application logs important events to the console. Run from terminal to see detailed logging.

## Development

### Project Structure

```
src/
├── config.py          # Configuration management
├── indexer.py         # Document indexing with LlamaIndex
├── query_engine.py    # Query processing and retrieval
└── chat_agent.py      # Agno agent with chat capabilities

ui/
└── macos_app.py       # PyQt6 native macOS interface

config.yaml            # User configuration
requirements.txt       # Python dependencies
main.py               # Application entry point
```

### Adding New Features

1. **New file types**: Update `config.yaml` and add readers in `indexer.py`
2. **New agent capabilities**: Extend the `DocumentSearchTool` in `chat_agent.py`
3. **UI improvements**: Modify `macos_app.py`

## License

This project is licensed under the MIT License.