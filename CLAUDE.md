# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Database Guru is an AI-powered natural language to SQL query assistant. Users ask questions in plain English, and the system generates, executes, and self-corrects SQL queries using local LLMs via Ollama.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy 2.0 (async) + Python 3.11+
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS
- LLM: Ollama (local, primarily qwen2.5-coder:32b)
- Databases: SQLite for metadata, supports PostgreSQL/MySQL/SQLite/MongoDB/DuckDB for user databases

## Development Commands

### Backend Development

```bash
# Activate virtual environment
source venv/bin/activate

# Start backend server (with hot reload)
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
./run_tests.sh

# Run specific test file
./run_tests.sh tests/test_confidence_scorer.py

# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html

# Run specific test by name
python -m pytest tests/test_confidence_scorer.py::test_error_type_scoring -v

# Create sample database
python scripts/create_sample_db.py
```

### Frontend Development

```bash
# Start frontend dev server (with hot reload)
cd frontend
npm run dev

# Run tests
npm test

# Run tests in UI mode
npm run test:ui

# Build for production
npm run build

# Lint
npm run lint
```

### System Startup

```bash
# One-command startup (recommended)
chmod +x start.sh
./start.sh

# Stop all services
./stop.sh

# Ensure Ollama is running
ollama serve
# Or: brew services start ollama
```

## Architecture Overview

### Core Agent System

The system uses a multi-agent architecture with specialized agents that work together:

1. **Self-Correcting Agent** (`src/llm/self_correcting_agent.py`)
   - Main orchestrator for query processing
   - Handles retry logic with automatic error recovery
   - Integrates all other agents and components
   - Uses `AgentTrace` for execution transparency
   - Key method: `process_query()` - main entry point

2. **Conversational Memory Agent** (`src/llm/conversational_memory_agent.py`)
   - Manages conversation context for multi-turn dialogs
   - Retrieves recent queries from chat session history
   - Builds context-aware prompts with conversation history
   - Smart detection of contextual vs standalone questions (SECURITY FIXED: only triggers on question start)
   - **Production-grade security**: Uses `create_safe_context_prompt()` with prompt injection protection
   - Default 3-query window (configurable)
   - Key methods: `get_context()`, `build_context_prompt()`, `should_use_context()`

3. **Query Planning Agent** (`src/llm/query_planning_agent.py`)
   - Chain-of-thought reasoning for complex queries
   - Creates structured execution plans before SQL generation
   - Validates schema references and suggests corrections
   - 4x better accuracy on multi-table queries
   - Key method: `create_plan()` - generates `QueryPlan` dataclass

4. **Confidence Scorer** (`src/llm/confidence_scorer.py`)
   - Predicts success probability of SQL corrections (0.0-1.0)
   - 5 weighted factors: error type (30%), schema match (25%), historical success (20%), complexity (15%), similarity (10%)
   - Auto-skips corrections below 20% confidence
   - Key method: `score_correction()` - returns `ConfidenceScore` dataclass

5. **Result Verification Agent** (`src/llm/result_verification_agent.py`)
   - Validates query results for logical correctness
   - Detects empty results, NULL values, extreme values, suspicious counts
   - Triggers re-generation on high-confidence issues
   - Key method: `verify_result()` - returns `VerificationResult`

6. **Correction Learner** (`src/llm/correction_learner.py`)
   - Learns from successful corrections for instant future fixes
   - 50% faster recovery on repeated errors
   - Pattern-based matching with fuzzy similarity
   - Key methods: `learn_correction()`, `try_apply_learned_fix()`

7. **Schema-Aware Fixer** (`src/llm/schema_aware_fixer.py`)
   - Fast typo correction without LLM calls (200x faster)
   - Uses fuzzy matching against actual schema
   - Handles table names, column names, and common SQL errors
   - Key method: `try_quick_fix()` - returns corrected SQL or None

8. **Prompt Sanitizer** (`src/security/prompt_sanitizer.py`) **NEW - November 2, 2025**
   - Multi-layer prompt injection protection
   - Input sanitization (removes control chars, normalizes whitespace)
   - Injection detection (15+ attack patterns blocked)
   - Safe prompt construction with XML-like delimiters
   - Token limits (500 chars for questions, 8000 for prompts)
   - Defense in depth: API → Agent → Prompt layers
   - Key methods: `sanitize_input()`, `detect_injection_attempts()`, `create_safe_context_prompt()`

### Data Flow

```
Natural Language Query (with optional session_id)
  ↓
Input Sanitization (Prompt Sanitizer) → Removes control chars, checks token limits **NEW**
  ↓
Injection Detection → Blocks 15+ attack patterns **NEW**
  ↓
Conversational Memory Agent → Retrieves conversation history (if session_id provided)
  ↓                          → Builds secure context-aware prompt with safe delimiters **UPDATED**
  ↓
Query Planning Agent → Creates structured plan with schema validation
  ↓
SQL Generator → Generates SQL from validated plan (with context if applicable)
  ↓
Confidence Scorer → Predicts success probability
  ↓
SQL Executor → Executes with timeout/safety limits
  ↓
Result Verification Agent → Validates logical correctness
  ↓
[If Error] → Schema-Aware Fixer (instant) → Correction Learner (learned patterns) → Self-Correcting Agent (LLM retry)
  ↓
[If Success] → Learn correction pattern for future
  ↓                          → Save to chat history (if session_id provided)
  ↓
Return Results
```

### Key Architectural Patterns

**Multi-Database Support:**
- `UserDatabaseConnector` (`src/core/user_db_connector.py`) - Creates connections to user databases
- `MultiDatabaseHandler` (`src/core/multi_db_handler.py`) - Handles parallel queries across multiple databases
- Supports both sync (DuckDB) and async (PostgreSQL, MySQL, SQLite) sessions
- Schema introspection parallelized for performance

**Schema Management:**
- `SchemaInspector` (`src/core/schema_inspector.py`) - Introspects database schemas
- `SchemaValidator` (`src/core/schema_validator.py`) - Validates table/column references with fuzzy matching
- `LocationMapper` (`src/core/location_mapper.py`) - Converts location names to database codes (e.g., "New York" → "NY")
- Schema sampling for value-aware validation

**Execution Safety:**
- `SQLExecutor` (`src/core/executor.py`) - Executes SQL with timeout protection and row limits
- Default: 1000 row limit, 30 second timeout
- Handles both async and sync database sessions
- Automatic truncation with warnings

**Caching & Performance:**
- Redis caching for query results (`src/cache/redis_client.py`)
- Rate limiting middleware (100 requests/60 seconds)
- Async operations throughout for concurrency

**User Feedback System:**
- Users can correct SQL/schema errors via UI
- `FeedbackValidator` (`src/llm/feedback_validator.py`) - Validates feedback before auto-learning
- 3 validation modes: strict (production), moderate (balanced), lenient (testing)
- Blocks destructive operations (DELETE, UPDATE, DROP) from auto-learning
- Comprehensive testing validates corrections actually improve results

**Security System (NEW - November 2, 2025):**
- `PromptSanitizer` (`src/security/prompt_sanitizer.py`) - Multi-layer prompt injection protection
- Input sanitization at API boundary (Pydantic validators)
- Injection detection (15+ attack patterns)
- Safe prompt construction with XML-like delimiters
- Token limits prevent resource exhaustion
- Security logging for monitoring
- 29 comprehensive security tests passing

### Database Schema

The system maintains its own metadata database (`database_guru.db`):

**Key Tables:**
- `database_connections` - User database connection configs
- `query_history` - All executed queries with results
- `chat_sessions` - Conversation sessions with context
- `learned_corrections` - Patterns learned from successful fixes
- `confidence_scores` - Historical confidence predictions
- `user_feedback` - User-submitted corrections and reports
- `system_settings` - Configuration for auto-learning and validation

### API Structure

Endpoints organized by domain (`src/api/endpoints/`):
- `query.py` - Main query processing endpoint (supports session_id for conversational context)
- `multi_db_query.py` - Multi-database query handling
- `connections.py` - Database connection management
- `chat.py` - Chat session management + conversation context endpoints (GET/DELETE /sessions/{id}/context)
- `feedback.py` - User feedback submission and stats
- `learned_corrections.py` - View learned patterns
- `result_verification.py` - Manual result verification
- `query_planning.py` - Query plan generation
- `confidence.py` - Confidence scoring API (if exists)
- `settings.py` - System settings and configuration
- `schema.py` - Schema introspection
- `models.py` - Available Ollama models

## Important Implementation Details

### Testing Strategy

- Use `pytest` with async support (`pytest-asyncio`)
- Mock database connections with in-memory SQLite
- Mock Ollama LLM responses for deterministic tests
- Separate unit tests (`tests/unit/`) from integration tests (`tests/`)
- Test markers: `@pytest.mark.asyncio`, `@pytest.mark.integration`, `@pytest.mark.slow`

**Common Test Patterns:**
```python
# Mock database session
@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

# Mock Ollama client
class MockOllamaClient:
    async def generate(self, model: str, prompt: str):
        return {"response": "SELECT * FROM test_table"}
```

### Frontend Component Structure

Located in `frontend/src/`:
- `components/` - React components (QueryInterface, ConnectionManager, ConfidenceDisplay, ConversationContextPanel, etc.)
- `services/` - API client (`api.ts`) using axios
- `hooks/` - Custom React hooks (`useQuery`, `useConnections`, etc.)
- `types/` - TypeScript type definitions (includes ConversationContext types)
- Uses TanStack Query for server state management
- Zustand for client state (if used)

### LLM Prompts

All prompts in `src/llm/prompts.py`:
- Structured with clear examples
- Include schema context and database-specific syntax
- Use few-shot learning patterns
- Chain-of-thought prompting for complex queries

### Error Handling

- Self-correcting agent retries up to 3 times
- Each retry uses different strategy: quick fix → learned patterns → LLM regeneration
- Graceful fallbacks when agents fail
- Detailed error messages with context
- All errors logged with structured logging

### Configuration

Settings managed via Pydantic in `src/config/settings.py`:
- Environment variables from `.env` file
- Type-safe configuration with validation
- Default values for all settings
- Supports multiple deployment environments

## Development Workflow

### Adding a New Feature

1. **Backend**: Add endpoint in `src/api/endpoints/`, use existing patterns for database access and LLM integration
2. **Database Models**: Add SQLAlchemy models in `src/database/models.py` if needed
3. **Schemas**: Add Pydantic schemas in `src/models/schemas.py` for request/response
4. **Tests**: Add tests in `tests/` following existing test structure
5. **Frontend**: Add/modify components in `frontend/src/components/`
6. **API Integration**: Update `frontend/src/services/api.ts`

### Debugging Tips

- Backend logs to console and `backend.log`
- Frontend logs to console and `frontend.log`
- Use `logger.info()` extensively for debugging agent decisions
- Check `AgentTrace` steps in API responses for execution details
- Use `/api/docs` (Swagger UI) for API testing
- Enable verbose logging: `logging.getLogger("src").setLevel(logging.DEBUG)`

### Common Issues

**Ollama Connection**: Ensure Ollama is running (`ollama serve`) and the correct model is pulled
**Port Conflicts**: Kill processes on ports 3000/8000 before starting
**Schema Issues**: Check database connection is active and schema introspection works
**Async/Sync Mixing**: DuckDB uses sync sessions, others use async - `SQLExecutor` handles both
**Import Cycles**: Avoid circular imports between agents by importing within functions if needed

## Key Code Locations

- **Main application entry**: `src/main.py:54` - FastAPI app initialization
- **Query processing flow**: `src/api/endpoints/query.py:32` - `/api/query/` endpoint
- **Conversational memory**: `src/llm/conversational_memory_agent.py` - Context retrieval and management
- **Context endpoints**: `src/api/endpoints/chat.py` - GET/DELETE context endpoints
- **Self-correction logic**: `src/llm/self_correcting_agent.py:261` - `process_query()` method
- **Confidence scoring**: `src/llm/confidence_scorer.py:147` - `score_correction()` method
- **Multi-DB queries**: `src/core/multi_db_handler.py:96` - `execute_multi_db_query()` method
- **Schema validation**: `src/core/schema_validator.py` - `validate_schema_references()`
- **SQL execution**: `src/core/executor.py:42` - `execute_query()` with timeout handling
- **Security/Prompt Sanitization**: `src/security/prompt_sanitizer.py` - Input sanitization and injection detection (NEW)
- **Security Tests**: `tests/test_prompt_sanitizer.py` - 29 comprehensive security tests (NEW)

## Documentation

Key docs in `docs/`:
- `CONVERSATIONAL_MEMORY_IMPLEMENTATION.md` - Conversational memory technical guide (UPDATED with security)
- `PHASE_1_COMPLETE.md` - Conversational memory completion summary (UPDATED with security)
- `TEST_CONVERSATIONAL_MEMORY.md` - Conversational memory testing guide
- `SECURITY_IMPROVEMENTS.md` - Recent security fixes and remaining issues (NEW - Nov 2, 2025!)
- `FUTURE_PLANS.md` - Prioritized roadmap with security fixes (NEW - Nov 2, 2025!)
- `QUERY_PLANNING_AGENT.md` - Query planning system deep dive
- `CONFIDENCE_SCORING.md` - Confidence scoring system
- `LEARNING_FROM_CORRECTIONS.md` - Correction learning system
- `RESULT_VERIFICATION_AGENT.md` - Result verification details
- `AUTO_LEARNING_GUIDE.md` - User feedback and auto-learning
- `MULTI_DATABASE_GUIDE.md` - Multi-database queries
- `SECURITY_POLICY.md` - Security controls and validation (UPDATED with prompt injection)
- `tests/TESTING.md` - Testing guide
