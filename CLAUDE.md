# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Database Guru is an AI-powered natural language to SQL query assistant. Users ask questions in plain English, and the system generates, executes, and self-corrects SQL queries using local LLMs via Ollama.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy 2.0 (async) + Python 3.11+
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS
- LLM: Ollama (local, primarily llama3.2:latest)
- Databases: SQLite for metadata, supports PostgreSQL/MySQL/SQLite/MongoDB/DuckDB for user databases

## Development Commands

After completing a task that involves tool use, provide a quick summary of the work you've done.

### Backend
```bash
source venv/bin/activate                    # Activate venv
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000  # Start server
./run_tests.sh                              # Run all tests
./run_tests.sh tests/test_file.py           # Run specific test
python -m pytest tests/ --cov=src --cov-report=html  # Coverage
```

### Frontend
```bash
cd frontend
npm run dev      # Start dev server
npm test         # Run tests
npm run build    # Production build
npm run lint     # Lint
```

### System
```bash
./start.sh       # Start all services (local dev)
./stop.sh        # Stop all services (local dev)
ollama serve     # Ensure Ollama is running
```

### Docker
```bash
docker compose up -d                           # Default: SQLite + BYO LLM
docker compose --profile ollama up -d          # + bundled Ollama
docker compose --profile full up -d            # + PostgreSQL + Redis
docker compose --profile full --profile ollama up -d  # Everything
docker compose build                           # Rebuild after code changes
docker compose down                            # Stop all
docker compose down -v                         # Stop + remove volumes
```

## Architecture Overview

The system uses a multi-agent architecture with 23+ specialized agents. See [.claude/AGENTS.md](.claude/AGENTS.md) for detailed agent documentation.

### Key Agents (Quick Reference)
| Agent | File | Purpose |
|-------|------|---------|
| Self-Correcting | `src/llm/self_correcting_agent.py` | Main orchestrator, parallel corrections |
| Conversational Memory | `src/llm/conversational_memory_agent.py` | Multi-turn dialog context |
| Query Planning | `src/llm/query_planning_agent.py` | Chain-of-thought reasoning |
| Confidence Scorer | `src/llm/confidence_scorer.py` | Success probability prediction |
| Multi-DB Handler | `src/core/multi_db_handler.py` | Parallel database execution |
| File Source Handler | `src/core/file_source_handler.py` | CSV/Excel file processing (Phase 13) |
| File Source Session | `src/core/file_source_session.py` | DuckDB session for file queries |
| Result Narrator | `src/llm/result_narrator.py` | Human-readable insights, tiered prompts, parallel analysis (Phase 19) |
| Model Router | `src/llm/model_router.py` | Per-task model selection |
| SQL Lineage Parser | `src/lineage/sql_lineage_parser.py` | Column-level lineage |
| Lineage Narrator | `src/lineage/lineage_narrator.py` | LLM-powered lineage explanations (Phase 12.1) |
| Impact Advisor | `src/lineage/impact_advisor.py` | Migration plans & SQL patches (Phase 12.2) |
| Schema Health Analyzer | `src/lineage/schema_health_analyzer.py` | Database design quality (Phase 12.3) |
| Pattern Intelligence | `src/lineage/pattern_intelligence.py` | Query pattern insights (Phase 12.4) |
| Lineage Conversation | `src/lineage/lineage_conversation_agent.py` | Natural language Q&A (Phase 12.5) |
| LLM Usage Tracker | `src/services/llm_usage_tracker.py` | Token & cost tracking (Phase 16) |
| Narrative Tiers | `src/llm/prompts/narrative_tiers.py` | Model-size-aware prompt templates (Phase 19) |
| Analytics Cache | `src/services/analytics_cache.py` | Two-tier stats/pattern cache (Phase 19) |

### Data Flow
```
Natural Language Query → Input Sanitization → Injection Detection
  → Conversational Memory → Tool-Using Agent → Query Planning
  → SQL Generator → Confidence Scorer → SQL Executor
  → Result Verification → [If Error: Parallel Corrections]
  → [If Success: Learn Pattern] → Parallel Analysis (stats/anomalies/correlations)
  → Tiered Narrative Generation → Return Results
```

### Detailed References
- **[.claude/AGENTS.md](.claude/AGENTS.md)** - All 18 agents with methods and features
- **[.claude/ARCHITECTURE.md](.claude/ARCHITECTURE.md)** - Architectural patterns (pooling, caching, security)
- **[.claude/API.md](.claude/API.md)** - All API endpoints by category
- **[.claude/CODE_LOCATIONS.md](.claude/CODE_LOCATIONS.md)** - Quick lookup for key code locations
- **[.claude/FRONTEND.md](.claude/FRONTEND.md)** - Frontend components and structure

## Development Workflow

### Adding a New Feature
1. **Backend**: Add endpoint in `src/api/endpoints/`
2. **Database Models**: Add SQLAlchemy models in `src/database/models.py`
3. **Schemas**: Add Pydantic schemas in `src/models/schemas.py`
4. **Tests**: Add tests in `tests/`
5. **Frontend**: Add components in `frontend/src/components/`
6. **API Integration**: Update `frontend/src/services/api.ts`

### Testing Strategy
- Use `pytest` with async support (`pytest-asyncio`)
- Mock database connections with in-memory SQLite
- Mock Ollama LLM responses for deterministic tests
- Test markers: `@pytest.mark.asyncio`, `@pytest.mark.integration`, `@pytest.mark.slow`

### Common Issues
| Issue | Solution |
|-------|----------|
| Ollama Connection | Ensure `ollama serve` is running and model is pulled |
| Port Conflicts | Kill processes on ports 3000/8000 |
| Schema Issues | Check database connection is active |
| Async/Sync Mixing | DuckDB uses sync sessions, `SQLExecutor` handles both |
| Import Cycles | Import within functions if needed |

### Debugging Tips
- Backend logs to console and `backend.log`
- Use `logger.info()` for agent decisions
- Check `AgentTrace` in API responses
- Use `/api/docs` (Swagger UI) for API testing

## Configuration

Settings in `src/config/settings.py`:
- Environment variables from `.env` file
- Type-safe with Pydantic validation
- Supports multiple deployment environments

## Documentation

Key docs in `docs/`:

| Category | Key Files |
|----------|-----------|
| **Guides** | `guides/MULTI_DATABASE_GUIDE.md`, `guides/CONNECTION_POOLING_GUIDE.md`, `guides/DATA_LINEAGE_GUIDE.md`, `guides/LINEAGE_INTELLIGENCE_USER_GUIDE.md`, `guides/FILE_DATA_SOURCE_USER_GUIDE.md` |
| **Technical** | `technical/PARALLEL_EXECUTION.md`, `technical/SEMANTIC_CACHING.md`, `technical/SQL_GENERATION_PIPELINE.md` |
| **Modules** | `modules/QUERY_PLANNING_AGENT.md`, `modules/TOOL_USING_AGENT.md` |
| **Testing** | `guides/testing/LINEAGE_INTELLIGENCE_TESTING.md`, `guides/testing/DATA_INSIGHTS_TESTING.md`, `guides/testing/TESTING_GUIDE.md` |
| **Planning** | `planning/FUTURE_PLANS.md`, `planning/MASTER_ROADMAP.md` |
| **LLM Usage** | `guides/LLM_USAGE_MONITORING_GUIDE.md` |
| **Data Insights** | `planning/DATA_INSIGHTS_ENHANCEMENT_PLAN.md` |
| **Deployment** | `guides/DOCKER_DEPLOYMENT_GUIDE.md`, `planning/DOCKER_CONTAINERIZATION_PLAN.md` |
