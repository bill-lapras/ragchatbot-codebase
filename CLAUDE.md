# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Quick start using shell script
chmod +x run.sh
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

Always run the server with `uv`. Never use `pip` directly.

### Environment Setup
```bash
# Install dependencies
uv sync

# Add new dependencies (use uv instead of pip)
uv add package_name

# Environment variables (.env file, loaded by python-dotenv in backend/config.py)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
# Optional:
ANTHROPIC_MODEL=claude-sonnet-4-20250514   # default if unset
ANTHROPIC_BASE_URL=                        # empty = api.anthropic.com
```

#### Using the Spotify Taskforce gateway
Keys from taskforce.spotify.net/api-keys only work against the gateway, not api.anthropic.com. `TASKFORCE_API_KEY` is exported in `~/.zshrc`, and `.env` references it:
```bash
ANTHROPIC_API_KEY=${TASKFORCE_API_KEY}   # braces required; dotenv won't expand $VAR
ANTHROPIC_BASE_URL=https://hendrix-genai.spotify.net/taskforce/anthropic
ANTHROPIC_MODEL=claude-sonnet-4-5
```
When `ANTHROPIC_BASE_URL` is set, `AIGenerator` also sends the gateway's `apikey` header. Start the server from a shell that has loaded `~/.zshrc` (e.g. `zsh -ic './run.sh'` from a non-interactive shell), or the key resolves to empty.

### Testing
```bash
cd backend && uv run pytest -q
```
Tests live in `backend/tests/` (fixtures in `conftest.py`). `Config` reads env vars per instance, so tests that check defaults must clear the environment (`patch.dict(os.environ, {}, clear=True)`) to avoid picking up `.env`.

### Python Execution
Always use `uv` for running Python files and commands:
```bash
# Run Python scripts
uv run python script.py

# Run any Python command
uv run command_name
```

### Code Quality Tools

#### Prerequisites
Install development dependencies before using code quality tools:
```bash
uv sync --group dev
```

#### Available Scripts

**Format Script (Modifies Files)**
```bash
./scripts/format.sh
```
Use this script when you want to automatically fix code style issues. It will:
1. Sort imports with isort
2. Format code with Black 
3. Run flake8 linting (reports remaining issues)
4. Run mypy type checking

**Lint Script (Read-Only Checks)**
```bash
./scripts/lint.sh
```
Use this script to verify code quality without modifying files. Perfect for:
- Pre-commit checks
- CI/CD pipelines
- Verifying code before submitting PRs

Exit code 0 = all checks pass, non-zero = issues found.

#### Troubleshooting
If scripts aren't executable: `chmod +x scripts/*.sh`

### Application Access
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture Overview

This is a Retrieval-Augmented Generation (RAG) system for course materials with a FastAPI backend and vanilla JavaScript frontend.

### Core Components

**RAGSystem (backend/rag_system.py)**: Main orchestrator that coordinates all components
- Manages document processing, vector storage, AI generation, and search tools
- Handles course document ingestion from the docs/ directory
- Processes queries using tool-based search approach

**VectorStore (backend/vector_store.py)**: ChromaDB-based vector storage with dual collections
- `course_catalog`: Stores course titles for name resolution
  - Metadata: title, instructor, course_link, lesson_count, lessons_json (list of lessons with lesson_number, lesson_title, lesson_link)
- `course_content`: Stores text chunks for semantic search
  - Metadata: course_title, lesson_number, chunk_index
- Supports filtered search by course name and lesson number

**AIGenerator (backend/ai_generator.py)**: Anthropic Claude API integration
- Model from `ANTHROPIC_MODEL` (default claude-sonnet-4-20250514); optional `ANTHROPIC_BASE_URL` gateway
- Up to 2 rounds of tool calls, then a final call without tools (max 3 API calls per query)
- Receives conversation history (from SessionManager, via RAGSystem) in the system prompt

**Search Tools (backend/search_tools.py)**: Tool-based search system
- CourseSearchTool (`search_course_content`): Semantic search across course content with course name resolution; records sources/links for the UI and clears them at the start of each search
- CourseOutlineTool (`get_course_outline`): Returns a course's title, link, and lesson list from the catalog
- ToolManager: Registers tools, routes Claude's tool calls, and collects/resets sources. It holds no data; only VectorStore talks to ChromaDB

**SessionManager (backend/session_manager.py)**: In-memory chat history per session (lost on restart)

### Data Flow
1. Course documents are loaded from docs/ directory on startup (PDF/DOCX pass the extension filter but are read as UTF-8 text, so only .txt parses correctly)
2. DocumentProcessor chunks content and extracts course metadata
3. VectorStore stores both metadata and content in separate ChromaDB collections
4. User queries trigger AI generation with access to search tools
5. AI uses CourseSearchTool to find relevant content and generates responses
6. Frontend displays responses with source attribution

### Key Configuration (backend/config.py)
- Chunk size: 800 characters with 100 character overlap
- Embedding model: all-MiniLM-L6-v2 (SentenceTransformers)
- Max search results: 5 per query
- Conversation history: 2 message pairs

### Frontend Architecture
- Single-page application with vanilla JavaScript
- Real-time course statistics display
- Markdown rendering support for AI responses
- Responsive design with sidebar for course info and suggested queries

## Development Notes

- The system automatically loads documents from docs/ on startup
- ChromaDB data persists in backend/chroma_db/
- Ingestion skips courses whose title is already stored, so edited course files are not re-indexed; delete backend/chroma_db/ to rebuild
- Course files must start with `Course Title:` / `Course Link:` / `Course Instructor:` lines, followed by `Lesson N: <title>` markers (optional `Lesson Link:` on the next line)
- The `/api/query` endpoint is async but makes synchronous Anthropic and ChromaDB calls, which block the event loop
- FastAPI serves both API endpoints (/api/*) and static frontend files
- CORS is configured for development with broad permissions
- No-cache headers are set for static files during development