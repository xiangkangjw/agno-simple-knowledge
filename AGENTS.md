# Repository Guidelines

## Project Structure & Module Organization
- `main.py` remains for legacy launchers and now directs developers to the Tauri workflow.
- `src/` hosts core logic: `config.py` loads YAML and env vars, `indexer.py` ingests files, `query_engine.py` serves retrieval, and `chat_agent.py` wires Agno tools.
- `config.yaml` holds runtime tuning, while design notes live in `knowledge-system-design-v1.md`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` prepares an isolated environment.
- `pip install -r requirements.txt` installs Agno, LlamaIndex, ChromaDB, and UI dependencies.
- `npm run tauri:dev` launches the desktop app alongside the FastAPI backend.
- `npm run tauri:build` creates a distributable bundle.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indentation, snake_case for functions, and CapWords for classes.
- Mirror the existing pattern of module docstrings, guard clauses, and informative logging (`chat_agent.py`).
- Keep configuration access centralized in `src/config.py` and expose new settings via typed properties.

## Testing Guidelines
- Use `pytest` with files under `tests/` that mirror `src/` modules (e.g., `tests/test_query_engine.py`).
- Stub OpenAI and filesystem calls so tests cover indexing edge cases and query fallbacks without network access.
- Run `pytest` before opening a PR and capture relevant logs when fixtures rely on sample documents.

## Commit & Pull Request Guidelines
- With no commit history yet, adopt Conventional Commits (`feat:`, `fix:`, `docs:`) and keep subjects under 72 characters.
- Group related changes per commit and split configuration or dependency updates into dedicated commits.
- PRs should include a summary, test results, screenshots or CLI snippets for UI changes, and call out follow-up index rebuild steps.

## Security & Configuration Tips
- Keep secrets in `.env`; extend `.env.example` when adding required keys and document them here.
- Scrutinize `config.yaml` changes so user-specific paths or tokens never reach version control.
- Scope document indexing to trusted directories to avoid accidentally embedding sensitive files.
