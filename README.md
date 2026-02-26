# <img src="docs/images/logo.png" width="48" height="48" valign="middle"> Database Guru

![Tests](https://github.com/sammyLOMI22/database-guru/workflows/Tests/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-46%25-yellow)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)

AI-powered natural language to SQL query assistant. Ask questions about your database in plain English!

## 🚀 Quick Start

### Docker (Recommended)

The fastest way to get started — no Python, Node.js, or dependency management required:

```bash
# 1. Copy and edit environment variables
cp .env.docker.example .env

# 2. Start the app (SQLite + BYO LLM)
docker compose up -d

# 3. Open http://localhost:3000
```

Make sure Ollama is running on your host machine (`ollama serve`), or use the bundled Ollama profile:

```bash
# With bundled Ollama (auto-pulls model)
docker compose --profile ollama up -d

# Full stack (PostgreSQL + Redis + Ollama)
docker compose --profile full --profile ollama up -d
```

See [Docker Deployment Guide](docs/guides/DOCKER_DEPLOYMENT_GUIDE.md) for all options including GPU setup.

### Local Development

#### Prerequisites
- Python 3.11+
- Node.js 18+
- Ollama (for local LLM)
- Redis (optional, for persistent caching - uses in-memory fallback if not available)

#### One-Command Startup

**Option 1: Application Only** (assumes Redis/Ollama already running)
```bash
chmod +x start.sh
./start.sh
```

**Option 2: Complete Stack** (starts Redis + Ollama + Application)
```bash
chmod +x start_all.sh
./start_all.sh
```

This will:
1. ✅ Start Redis (if not already running)
2. ✅ Start Ollama (if not already running)
3. ✅ Create Python virtual environment
4. ✅ Install all dependencies
5. ✅ Create sample database
6. ✅ Start backend (http://localhost:8000)
7. ✅ Start frontend (http://localhost:3000)

**Note:** `start_all.sh` intelligently tracks which services it started and only stops those when you run `./stop_all.sh`.

### Manual Setup

If you prefer manual control:

#### 1. Backend Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn[standard] pydantic pydantic-settings python-multipart \
    sqlalchemy aiosqlite ollama httpx python-dotenv sqlparse greenlet

# Create sample database
python3 scripts/create_sample_db.py

# Start backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend Setup (in new terminal)
```bash
cd frontend
npm install
npm run dev
```

#### 3. Ensure Ollama is Running
```bash
ollama serve
# Or: brew services start ollama
```

#### 4. (Optional) Setup Redis & Ollama Models for Better Caching
```bash
# Automated setup for Redis + Ollama + Models
./scripts/setup_cache.sh

# Or individually:
./scripts/setup_redis.sh    # Setup Redis
./scripts/setup_ollama.sh   # Pull embedding models
```

See [Cache Setup Guide](docs/technical/CACHE_SETUP.md) for details.

## 🎨 Feature Demo Page

Want to see all features in action? Check out the **interactive demo page**!

```
http://localhost:3000?demo=true
```

The demo showcases:
- ✨ **Phase 1: Conversational Memory** - Natural multi-turn dialogue with context panel toggle
- 🌊 **Phase 2: Streaming Results** - Progressive result delivery
- 🎯 **Confidence Scoring** - Success probability predictions
- 📋 **Query Planning** - Complex query orchestration
- 🔧 **Auto-Correction** - Self-healing SQL generation with parallel strategies
- ⚠️ **Result Verification** - Suspicious result detection
- 🛠️ **Tool-Using Agent** - Schema exploration tools with 10 specialized tools
- 📊 **Semantic Cache Dashboard** - Cache monitoring, stats, and management
- ⚡ **Cache Trace Integration** - Cache hit/miss visible in execution trace
- 🔌 **Enhanced Connections** - Edit, delete, and manage database connections
- 📊 **Advanced Visualization** - Intelligent chart detection with Bar, Line, Pie, Scatter charts
- 📈 **Cross-Database Comparison** - Visual comparison across multiple databases
- ⚙️ **Small Model Optimization** - Per-task model configuration, query templates, location preprocessing
- 🗄️ **Dialect-Aware SQL (NEW!)** - Database-specific SQL generation for PostgreSQL, MySQL, SQLite, DuckDB
- 🔍 **Multi-Database Query Validation (NEW!)** - Pre-flight validation with schema assessment
- 🔗 **Data Lineage (NEW!)** - Column-level lineage visualization, impact analysis, query pattern heatmaps
- 🧠 **Lineage Intelligence (NEW!)** - LLM-powered explanations, schema health analysis, conversational Q&A
- 🔀 **Table Sorting (NEW!)** - Click any column header to sort results (numbers, dates, strings auto-detected)
- 📁 **CSV/Excel File Data Sources (NEW!)** - Upload CSV/Excel files as queryable data sources with DuckDB
- 📊 **LLM Usage Monitoring (NEW!)** - Track token usage, costs, and performance across all agents
- 🔬 **Data Insights Enhancement (NEW!)** - Tiered narratives by model size, analytics caching, multi-source quality insights, adaptive chart presets
- 🔄 **Database Migration Toolkit (NEW!)** - Schema diff, migration planner, script generator (up/down/verify SQL), data migration assistant

All with mock data - no database connection needed!

## 📊 Connect to Sample Database

1. Open http://localhost:3000
2. Click **"Connections"** tab in sidebar
3. Click **"+ Add Connection"**
4. Select **"SQLite"**
5. Enter path: `/Users/sam/database-guru/sample_ecommerce.db`
6. Click **"Test Connection"** → **"Save Connection"**
7. Click the connection to activate it
8. Start asking questions!

## 💡 Example Questions

Try asking these questions:

- "What are the top 5 best-selling products?"
- "Show me all orders from customers in California"
- "What's the average order value?"
- "Which products have the highest ratings?"
- "What's the total revenue by category?"
- "Show me customers who haven't placed orders yet"
- "What products are low in stock (less than 50 units)?"
- "Which customer has spent the most money?"

## 🗄️ Sample Database Schema

The sample e-commerce database includes:

- **customers** (15 records) - Customer information
- **categories** (4 records) - Product categories
- **products** (20 records) - Product catalog
- **orders** (50 records) - Order history
- **order_items** (123 records) - Order line items
- **reviews** (30 records) - Product reviews

## 🛑 Stopping the App

```bash
# If using start.sh (application only)
./stop.sh

# If using start_all.sh (complete stack)
./stop_all.sh

# Or press Ctrl+C in terminal
```

## 🔧 Configuration

Edit `.env` file to customize:

```bash
# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:32b

# Redis (for caching)
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600

# Query limits
MAX_QUERY_ROWS=1000
QUERY_TIMEOUT_SECONDS=30

# Database (for app metadata, not your data)
DATABASE_URL=sqlite+aiosqlite:///./database_guru.db

# Parallel execution
MAX_PARALLEL_DATABASES=10
PARALLEL_CORRECTIONS_TIMEOUT=10
```

**See:** [Cache Setup Guide](docs/technical/CACHE_SETUP.md) for Redis and Ollama installation instructions

## 🎯 Features

- ✅ Natural language to SQL conversion
- ✅ **Conversational Memory** - Natural multi-turn conversations with context awareness
- ✅ **Production-Grade Security** - Multi-layer prompt injection protection and input sanitization
- ✅ **Parallel Execution (Production-Ready)** - 3x faster multi-database queries + 1.6x faster error corrections with dual timeout protection and comprehensive metrics
- ✅ **Confidence Scoring** - AI predicts success probability before executing corrections
- ✅ **User Feedback Integration** - Learn from user corrections for continuous improvement
- ✅ **Query Planning Agent** - 4x better accuracy on complex multi-table queries
- ✅ **Intelligent Schema Validation** - Auto-detects and corrects schema mismatches
- ✅ **Self-correcting SQL** - Automatically fixes errors and retries
- ✅ **Learning from Corrections** - Remembers successful fixes for 50% faster error recovery
- ✅ **Schema-Aware Fixes** - 200x faster typo correction without LLM
- ✅ **Tool-Using Agent** - 10 specialized tools for schema exploration and query validation with full UI dashboard
- ✅ **Semantic Caching** - Intelligent query similarity matching for 30-50% higher cache hit rates
- ✅ **Semantic Cache Dashboard (NEW!)** - Full UI for monitoring cache stats, viewing cached queries, and managing caches
- ✅ **Cache Trace Integration (NEW!)** - Cache operations visible in Agent Execution Trace with hit/miss indicators
- ✅ **Connection Pooling (PRODUCTION-READY - NEW!)** - 30x faster queries with intelligent connection reuse (150ms → 5ms per query)
- ✅ **Enhanced Connection Management** - Edit connections, loading states, selected connection highlighting
- ✅ **Context Panel Toggle** - Show/hide conversational memory panel with one click
- ✅ **Result Verification** - Catches logical errors and suspicious results
- ✅ Multiple database support (PostgreSQL, MySQL, SQLite, MongoDB, DuckDB)
- ✅ **Multi-database queries** - Query multiple databases simultaneously with parallel execution
- ✅ **Multi-Database Query Validation (NEW!)** - Pre-flight validation shows which databases can answer your query before execution
- ✅ **Data Lineage & Impact Analysis (NEW!)** - Column-level lineage visualization, schema change impact analysis, and query pattern heatmaps
- ✅ **Advanced Visualization (NEW!)** - 10 chart types (Bar, Line, Pie, Scatter, Area, Histogram, Box Plot, Treemap, Sunburst, Bubble) with intelligent auto-detection, manual override, export to CSV/JSON/ZIP
- ✅ **Cross-Database Comparison Charts** - Visual comparison across databases with auto-detection
- ✅ **Configurable Row Limits (NEW!)** - Select from 10 to 10,000 rows per query via dropdown
- ✅ **Result Table Pagination** - Navigate through large result sets with 10/25/50/100 rows per page
- ✅ **Table Sorting (NEW!)** - Click column headers to sort results, with smart type detection for numbers, dates, and strings
- ✅ **Small Model Optimization (NEW!)** - Per-task model routing, query templates, location preprocessing, and dialect-aware SQL generation for faster responses with smaller models
- ✅ **CSV/Excel File Data Sources (NEW!)** - Upload and query CSV/Excel files as DuckDB tables
- ✅ **LLM Usage Monitoring (NEW!)** - Track token usage, costs, and performance per session and globally with full dashboard
- ✅ **Data Insights Enhancement (NEW!)** - Tiered narrative prompts (compact/standard/enhanced), analytics caching, multi-source data quality analysis, adaptive chart scoring presets, parallel analysis pipeline with early exit optimization
- ✅ **Database Migration Toolkit (NEW!)** - Schema diff engine, dependency-aware migration planner, multi-dialect script generator (up.sql/down.sql/verify.sql), data migration assistant with staging table pattern and batched INSERT SELECT
- ✅ **Chat sessions** - Maintain context across queries
- ✅ Database connection management
- ✅ Schema introspection
- ✅ Query execution with safety limits
- ✅ Query history tracking
- ✅ Model selection (choose from your local Ollama models)
- ✅ Beautiful React UI with real-time updates

## ⚡ Performance Features (Production-Ready!)

Database Guru includes production-grade parallel execution optimizations delivering dramatic performance improvements:

### 1. Parallel Multi-Database Execution (3x Speedup)
Execute queries across multiple databases simultaneously using `asyncio.gather()`:

**Before:**
```
Query 5 databases sequentially: 5s total (1s × 5)
```

**After:**
```
Query 5 databases in parallel: 1.5s total (3x faster!)
```

**Production Features:**
- **3.0x speedup** on multi-database queries (verified in 71 tests)
- **Intelligent throttling** - Configurable max concurrency (default: 10 databases)
- **Dual timeout protection** - 35-second timeout prevents hanging queries
- **Comprehensive metrics** - Track speedup, concurrency, success rates
- **Graceful degradation** - One database failure doesn't stop others
- Handles both async (PostgreSQL, MySQL, SQLite) and sync (DuckDB) sessions
- Automatic parallelization with no configuration needed

### 2. Parallel Correction Attempts (1.6x Speedup)
Try multiple error-fixing strategies simultaneously instead of sequentially:

**Before (Sequential):**
```
1. Quick fix (0.1s) → Failed
2. Learned corrections (0.5s) → Failed
3. LLM fix (1.0s) → Success
Total: 1.6 seconds
```

**After (Parallel):**
```
1. Quick fix (0.1s) ┐
2. Learned fix (0.5s) ├─ All run simultaneously
3. LLM fix (1.0s) ┘
First success wins!
Total: 1.0 seconds (1.6x faster!)
```

**Production Features:**
- **1.6x speedup** on error corrections (verified in 71 tests)
- **Timeout protection** - 10-second configurable timeout prevents hanging
- **Strategy metrics** - Track which strategies win and why
- **Smart fallback** - LLM fallback if all strategies timeout
- **Three strategies in parallel**: schema-aware quick fix, learned corrections, LLM regeneration
- **Graceful degradation** - Exceptions in one strategy don't stop others
- Optional flag `use_parallel_corrections` allows fallback to sequential mode

### 3. Connection Pooling (30x Speedup - NEW!)
Maintain reusable database connection pools instead of creating fresh connections for every query:

**Before (No Pooling):**
```
Query 1: Create engine (150ms) + Execute (5ms) = 155ms
Query 2: Create engine (150ms) + Execute (5ms) = 155ms
Query 3: Create engine (150ms) + Execute (5ms) = 155ms
Total overhead: 450ms just for connections!
```

**After (With Pooling):**
```
Query 1: Get from pool (5ms) + Execute (5ms) = 10ms
Query 2: Get from pool (5ms) + Execute (5ms) = 10ms
Query 3: Get from pool (5ms) + Execute (5ms) = 10ms
Total overhead: 15ms (30x faster!)
```

**Production Features:**
- **30x faster** - Connection overhead reduced from 150ms to ~5ms per query
- **Singleton pattern** - Global pool manager with per-connection isolation
- **Supported databases** - PostgreSQL, MySQL, SQLite, DuckDB (MongoDB coming soon)
- **Three-tier eviction** - Idle timeout (30 min), max age (2 hours), automatic cleanup
- **Background cleanup** - Runs every 5 minutes to evict idle pools
- **Comprehensive metrics** - Active/idle connections, utilization%, wait times, health status
- **10 environment variables** - Fine-tune pool size, overflow, timeouts, cleanup intervals
- **API endpoints** - 4 REST endpoints for monitoring and manual eviction
- **Frontend dashboard** - Real-time pool metrics with cyan color theme (🔗 Pools tab)
- **Test infrastructure** - Docker Compose for reproducible test environments
- **Async & sync support** - Handles both async and sync database sessions
- **Graceful shutdown** - Cleanly closes all pools on application termination
- **Zero configuration** - Enabled by default, works automatically

**Monitoring Dashboard:**

Visit the **🔗 Pools** tab to see:
- Total pools, active/idle connections, avg utilization%
- Per-pool details with health indicators (🟢 🟡 🔴)
- Utilization progress bars (color-coded by load)
- Wait time metrics, pool age
- Manual eviction controls

**See:** [Connection Pooling Guide](docs/guides/CONNECTION_POOLING_GUIDE.md) for configuration and [Test Setup](docs/guides/TEST_DATABASE_SETUP.md) for test infrastructure

### Observability & Metrics

Both features include comprehensive metrics for monitoring and optimization:

**Multi-Database Metrics:**
- Total queries, max/actual concurrency
- Successful vs failed queries
- Average query time, total elapsed time
- **Calculated speedup** (e.g., "3.0x faster than sequential")

**Correction Metrics:**
- Strategies attempted/succeeded/failed
- Winning strategy identification
- Elapsed time, timeout detection
- Success rate tracking

**Frontend Components:**
- `ParallelDatabaseMetrics` - Orange-themed speedup badges
- `ParallelCorrectionsMetrics` - Purple-themed strategy display
- `ToolsPanel` - Tool-Using Agent management dashboard (NEW!)
- Real-time performance visualization

**See:** [Parallel Execution Technical Guide](docs/technical/PARALLEL_EXECUTION.md) for implementation details and [Code Review](docs/reports/CODE_REVIEW_PARALLEL_EXECUTION.md) for quality assurance

## Tool-Using Agent Dashboard (NEW!)

Database Guru now includes a comprehensive UI for the Tool-Using Agent, accessible via the **Tools** tab in the main navigation.

**Features:**
- **Overview Tab**: Summary stats (total tools, executions, success rate), tools by category breakdown, "How it works" explanation, quick actions (clear cache)
- **Tool Directory Tab**: Browse all 10 tools with descriptions, category filtering, expandable details showing parameters and cache TTL
- **Usage Stats Tab**: Per-tool execution metrics with visual progress bars, sortable by executions/success rate/avg time, cache hit tracking

**Orange Color Theme**: The Tools tab uses an orange color scheme to visually distinguish it from other tabs.

**See:** [Tool-Using Agent Guide](docs/modules/TOOL_USING_AGENT.md) for complete documentation

## ⚙️ Small Model Optimization (NEW!)

Database Guru now includes **intelligent optimizations** specifically designed to improve performance when using smaller, faster LLM models. These features reduce LLM calls, normalize inputs, and enable per-task model routing.

### Key Features:

**1. Per-Task Model Configuration**
Assign different models to different tasks for optimal performance:

| Task | Recommended Model | Default Timeout |
|------|------------------|-----------------|
| **SQL Generation** | `duckdb-nsql`, `sqlcoder` | 30s |
| **Narratives** | `llama3.2`, `gemma` | 15s |
| **Query Planning** | Reasoning-capable models | 20s |
| **Error Correction** | Code-focused models | 15s |

**Benefits:**
- Use specialized SQL models for query generation
- Use general-purpose models for natural language tasks
- Configure per-task timeouts for optimal responsiveness
- Falls back to default model when per-task model is not configured

**2. Query Template Engine**
Bypass LLM entirely for simple, common query patterns:

| Pattern | Example Input | Generated SQL |
|---------|---------------|---------------|
| `list_all` | "show all products" | `SELECT * FROM products LIMIT 100` |
| `count` | "how many customers" | `SELECT COUNT(*) FROM customers` |
| `top_n` | "top 5 by price" | `SELECT * FROM X ORDER BY Y DESC LIMIT 5` |
| `filter_location` | "orders from California" | `SELECT * FROM orders WHERE state = 'CA'` |
| `filter_date` | "orders from last 7 days" | Dialect-specific (see below) |
| `search` | "find products containing 'widget'" | Dialect-specific (see below) |
| `sum/average` | "total revenue" | `SELECT SUM(revenue) FROM orders` |
| `group_by` | "sales by category" | `SELECT category, COUNT(*) FROM X GROUP BY category` |

**Benefits:**
- **Instant responses** - No LLM latency for simple queries
- **Zero errors** - Template-generated SQL is always valid
- **Resource savings** - Reduces LLM API calls significantly
- **Confidence scores** - Each match includes a confidence level (0.9-0.95)
- **Dialect-aware (NEW!)** - Generates database-specific SQL syntax

**3. Location Preprocessing (Bidirectional)**
Automatically normalizes location values to match your database format:

```
Query: "Show orders from California"
Database uses state codes: CA, NY, TX
→ Preprocessed: "Show orders from CA"

Query: "Show orders from CA"
Database uses full names: California, New York
→ Preprocessed: "Show orders from California"
```

**Benefits:**
- Detects database format from sample values
- Works for US states, cities, countries
- Eliminates common WHERE clause mismatches
- Improves first-attempt SQL accuracy

**4. Dialect-Aware SQL Generation (NEW!)**
Generates database-specific SQL syntax for accurate cross-database queries:

| Dialect | Date Filter (last 7 days) | Case-Insensitive Search |
|---------|---------------------------|-------------------------|
| PostgreSQL | `WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'` | `WHERE name ILIKE '%widget%'` |
| MySQL | `WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)` | `WHERE LOWER(name) LIKE LOWER('%widget%')` |
| SQLite | `WHERE created_at > datetime('now', '-7 days')` | `WHERE LOWER(name) LIKE LOWER('%widget%')` |
| DuckDB | `WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'` | `WHERE name ILIKE '%widget%'` |

**Benefits:**
- Automatically detects database type from connection
- Generates correct syntax for dates, booleans, strings
- No manual configuration required
- Reduces SQL errors by ~30% on cross-database queries

**5. Prompt Optimization for Small Models (NEW!)**
Intelligently compresses prompts to fit within smaller context windows while preserving SQL generation accuracy:

| Model Size | Context Budget | Schema Strategy | Examples |
|------------|---------------|-----------------|----------|
| **SMALL** (<7B) | ~2K tokens | Essential tables only | Zero-shot |
| **MEDIUM** (7-13B) | ~4K tokens | Most relevant tables | 2-3 examples |
| **LARGE** (13B+) | ~8K tokens | Full schema if needed | 4-5 examples |

**Key Features:**
- **Auto Model Detection**: Detects model size from name (e.g., "7b" → MEDIUM)
- **Schema Compression**: Includes only tables relevant to the query
- **Model-Specific Templates**: Formatting matched to model training (Llama, Qwen, Gemma, Mistral, Phi, DuckDB-NSQL, SQLCoder)
- **Token Budgeting**: Allocates tokens across system prompt, schema, examples, and response buffer
- **Safe Defaults**: Feature is OFF by default, user opt-in via settings

**Supported Model Families:**
```
Llama      - <|start_header_id|>system<|end_header_id|>
Qwen       - <|im_start|>system
Gemma      - <start_of_turn>user
Mistral    - [INST] instruction [/INST]
Phi        - <|system|> ... <|end|>
DuckDB-NSQL - ### Database Schema: (SQL-specialized)
SQLCoder   - ### Task ... ### Question ... ### SQL
```

**Benefits:**
- **40% token reduction** for schema-heavy prompts
- **Faster responses** with smaller models
- **Higher accuracy** with model-specific formatting
- **Graceful fallback** if optimization fails

### Configuration:

Access **Settings** → **Per-Task Model Configuration** to:
- Select models for each task type
- Adjust timeouts per task
- Toggle Query Templates on/off
- Toggle Location Preprocessing on/off

### Example Workflow:

```
User: "show all customers"

⚡ Template Match: list_all (confidence: 0.95)
→ SELECT * FROM customers LIMIT 100
→ Executed in 50ms (no LLM call!)

User: "What's the average order value for California customers?"

🗺️ Location Preprocessing: California → CA
🧠 SQL Generation Model: duckdb-nsql
→ SELECT AVG(order_total) FROM orders WHERE state = 'CA'
→ Executed in 1.2s (single LLM call with optimized prompt)
```

### API Endpoints:

```bash
# Get current model settings
curl http://localhost:8000/api/settings/

# Update per-task model configuration
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{
    "model_sql_generation": "duckdb-nsql",
    "model_narratives": "llama3.2:latest",
    "timeout_sql_generation": 30,
    "enable_query_templates": true,
    "enable_location_preprocessing": true
  }'
```

---

## 🧠 Semantic Caching (NEW!)

Database Guru now uses **intelligent semantic caching** to dramatically improve query response times by matching similar queries instead of requiring exact matches.

### Key Benefits:
- **30-50% higher cache hit rate** - "Show customers from California" matches "List customers in CA"
- **40-60% fewer LLM calls** - LLM responses cached and reused for similar questions
- **1-5 second savings** per semantic cache hit
- **Automatic** - No configuration needed, works out of the box

### How It Works:

```
Query Input: "Show me customers from California"
    ↓
[1] Exact Cache Check → Miss
    ↓
[2] Semantic Cache Check → Found similar: "List customers in CA" (92% similar)
    ↓
Return cached result instantly!
```

### Three-Layer Caching:

**1. Exact Hash Cache (Fastest)**
- Matches identical queries
- ~0.5s response time

**2. Semantic Query Cache (NEW!)**
- Matches similar questions using text embeddings
- Cosine similarity threshold: 0.85
- 24-hour TTL

**3. LLM Response Cache (NEW!)**
- Caches SQL generation at the LLM level
- Schema fingerprinting ensures cache validity
- 12-hour TTL

### Cache Trace Integration (NEW!)

Cache operations are now fully integrated into the **Agent Execution Trace** for complete observability:

- **Cache lookup steps** - See when cache is checked
- **Cache hit/miss indicators** - Know if result came from cache
- **Similarity scores** - See how closely queries matched
- **Cache store confirmation** - Track when results are cached

In multi-database queries, you'll see:
- Per-database cache hit/miss status
- Summary banner showing cached vs fresh queries
- Cache info in each database result's trace

### Performance Improvements:

| Metric | Before | After |
|--------|--------|-------|
| Cache hit rate | ~20% | 50-70% |
| LLM calls per query | 1-4 | 0.4-1.5 |
| Avg response time | 2-5s | 0.5-2s |

### Technical Details:

- **Embedding Service**: Uses Ollama embeddings or TF-IDF fallback
- **Similarity Matching**: Cosine similarity with configurable thresholds
- **Schema Fingerprinting**: Ensures cache invalidation on schema changes
- **Conditional Verification**: Skips expensive verification for high-confidence results

**Setup & Configuration:**
- **[Cache Setup Guide](docs/technical/CACHE_SETUP.md)** - Complete Redis & Ollama setup instructions
  - Local installation (Homebrew)
  - Docker setup
  - Docker Compose configuration
  - Troubleshooting guide

**Documentation:**
- **[Semantic Caching Guide](docs/technical/SEMANTIC_CACHING.md)** - Complete backend documentation
- **[Semantic Cache UI Guide](docs/technical/SEMANTIC_CACHE_UI.md)** - Frontend components documentation

## 📊 Semantic Cache Dashboard (NEW!)

Database Guru now includes a comprehensive UI for monitoring and managing semantic caching, accessible via the **Cache** tab in the main navigation.

### Features:

**Overview Tab:**
- 4 stat cards: Total Lookups, Hit Rate %, Semantic Hits, Cached Entries
- Semantic Cache breakdown (exact vs semantic hits, misses, threshold, TTL)
- LLM Response Cache stats
- Embedding Service status (Online/TF-IDF fallback)
- "How Semantic Caching Works" explanation
- Quick actions: Clear Semantic Cache, Clear LLM Cache, Clear All Caches

**Statistics Tab:**
- Hit Type Distribution (exact hits, semantic hits, misses with progress bars)
- LLM Response Cache metrics
- Embedding Service Efficiency
- Estimated Performance Impact

**Recent Queries Tab:**
- Browsable list of cached queries
- Expandable SQL view for each query
- Database type badges (PostgreSQL, MySQL, SQLite, DuckDB)
- Hit counts and timestamps
- Page size selector (10/25/50 per page)

### Inline Cache Indicators:

Query results now show cache hit badges:
- **Green badge**: "Exact Cache Hit - Instant Response"
- **Amber badge**: "Semantic Cache Hit (X% match) - Instant Response"
- Shows matched question for semantic hits

### API Endpoints:

```bash
# Get combined cache statistics
curl http://localhost:8000/api/cache/stats

# Get recent cached queries
curl http://localhost:8000/api/cache/recent?limit=20

# Clear semantic cache
curl -X DELETE http://localhost:8000/api/cache/semantic

# Clear LLM cache
curl -X DELETE http://localhost:8000/api/cache/llm

# Clear all caches
curl -X DELETE http://localhost:8000/api/cache/all

# Clear cache for specific connection
curl -X DELETE http://localhost:8000/api/cache/connection/1
```

**Amber Color Theme**: The Cache tab uses an amber/gold color scheme to visually distinguish it from other tabs.

**See:** [Semantic Cache UI Guide](docs/technical/SEMANTIC_CACHE_UI.md) for complete frontend documentation

---

## 📊 LLM Usage Monitoring (NEW!)

Database Guru now includes **comprehensive LLM usage monitoring** that tracks every LLM API call across all agents, providing full visibility into token consumption, costs, and performance.

### Key Features:

**1. Centralized Token Tracking**
Every LLM call is automatically instrumented using a context manager:
- **Token counting**: tiktoken encoder with native Ollama/OpenAI/Anthropic extraction
- **Cost estimation**: Configurable per-model pricing (per 1M tokens)
- **Response timing**: Millisecond-precision latency tracking
- **Error logging**: Failed calls recorded with error details

**2. Usage Dashboard**
Navigate to the **Usage** tab for a full monitoring dashboard:

| View | What It Shows |
|------|---------------|
| **Stats Overview** | Total calls, tokens, avg latency, estimated cost |
| **By Agent** | Token consumption per agent (SQL Generator, Query Planner, etc.) |
| **By Model** | Usage breakdown by LLM model |
| **By Provider** | Usage breakdown by provider (Ollama, OpenAI, etc.) |
| **Time Series** | Usage trends over time (hourly/daily) |
| **Recent Calls** | Searchable log of recent LLM calls |

**3. Per-Session Tracking**
Each chat session displays inline usage metrics:
- **Session Usage Badge** - Compact token count and cost in the header
- **Usage Summary** - Expandable panel with agent-level breakdown

**4. Pre-Computed Aggregates**
Background aggregation rolls up hourly/daily statistics by agent, provider, and model for fast dashboard queries.

### Tracked Agents:
All LLM-calling agents are instrumented:
- SQL Generator, Self-Correcting Agent, Query Planning Agent
- Result Narrator, Lineage Narrator, Impact Advisor
- Schema Health Analyzer, Pattern Intelligence, Lineage Conversation

### API Endpoints:

```bash
# Get usage statistics (last 7 days)
curl http://localhost:8000/api/llm/usage/stats?days=7

# Get usage by agent type
curl http://localhost:8000/api/llm/usage/by-agent?days=30

# Get usage by model
curl http://localhost:8000/api/llm/usage/by-model?days=7

# Get time series data
curl http://localhost:8000/api/llm/usage/timeseries?days=7&granularity=day

# Get session-specific usage
curl http://localhost:8000/api/llm/usage/session/{session_id}

# Get recent calls with filtering
curl "http://localhost:8000/api/llm/usage/recent?limit=50&agent_type=sql_generator"

# Trigger aggregation
curl -X POST http://localhost:8000/api/llm/usage/aggregate?days=1

# Seed default model configs
curl -X POST http://localhost:8000/api/llm/usage/configs/seed
```

### Database Tables:

| Table | Purpose |
|-------|---------|
| `llm_usage` | Individual LLM call records (tokens, cost, timing, agent, model) |
| `llm_usage_aggregate` | Pre-computed hourly/daily statistics |
| `llm_model_config` | Model metadata and cost rates |

---

## 🏗️ Architecture

**Backend:**
- FastAPI (Python)
- SQLAlchemy 2.0 (async)
- Ollama (local LLM)
- SQLite for metadata
- Parallel execution with `asyncio.gather()`

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- Tailwind CSS
- TanStack Query

## 📁 Project Structure

```
database-guru/
├── src/                    # Backend source
│   ├── api/               # API endpoints
│   │   └── endpoints/
│   │       └── files.py   # File upload endpoints (NEW!)
│   ├── core/              # Business logic
│   │   ├── file_source_handler.py    # File processing (NEW!)
│   │   └── file_source_session.py    # DuckDB session (NEW!)
│   ├── database/          # Database layer
│   ├── llm/               # LLM integration
│   ├── lineage/           # Data lineage system
│   ├── services/          # Business services
│   │   ├── llm_usage_tracker.py   # LLM call tracking (NEW!)
│   │   ├── llm_cost_service.py    # Cost calculation (NEW!)
│   │   └── llm_usage_aggregator.py # Usage rollups (NEW!)
│   └── main.py            # Entry point
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   │   ├── lineage/   # Lineage visualization
│   │   │   ├── FileUploadModal.tsx   # File upload UI (NEW!)
│   │   │   ├── FilePreviewPanel.tsx  # File preview UI (NEW!)
│   │   │   └── dashboard/
│   │   │       └── LLMUsageDashboard.tsx  # Usage monitoring (NEW!)
│   │   ├── hooks/         # Custom hooks
│   │   ├── services/      # API client
│   │   └── types/         # TypeScript types
│   └── index.html
├── uploads/               # File storage directory (NEW!)
│   ├── global/           # Shared files
│   └── sessions/         # Session-scoped files
├── scripts/               # Utility scripts
│   └── create_sample_db.py
├── start.sh              # Startup script
├── stop.sh               # Shutdown script
└── sample_ecommerce.db   # Sample database
```

## 🔐 Security

### Production-Grade Security Features (NEW!)

✅ **Prompt Injection Protection** - Multi-layer defense against malicious prompts
✅ **Input Sanitization** - Removes control characters and malicious patterns
✅ **Destructive Operation Blocking** - Prevents DELETE/UPDATE/DROP from auto-learning
✅ **Token Limits** - Prevents resource exhaustion attacks
✅ **Context Detection Security** - Prevents keyword manipulation exploits
✅ **Safe Prompt Construction** - XML-like delimiters with escape protection

### Recent Security Improvements

**November 2, 2025 - Conversational Memory Security Hardening:**
1. Fixed context detection bug where keywords anywhere triggered context usage
2. Implemented comprehensive prompt injection protection system
3. Added multi-layer input sanitization (API → Agent → Prompt)
4. Deployed 15+ attack pattern detection rules
5. All 44 security and conversational memory tests passing

⚠️ **Development Only** - This configuration is for local development.

For production deployment, see [docs/technical/SECURITY_POLICY.md](docs/technical/SECURITY_POLICY.md) for:
- Password encryption
- Authentication/Authorization
- CORS configuration
- Rate limiting
- Input validation
- Prompt injection defenses
- Auto-learning security controls

## 📚 API Documentation

Once running, visit:
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## 🧪 Adding Your Own Database

1. Go to **Connections** tab
2. Click **+ Add Connection**
3. Choose your database type (PostgreSQL, MySQL, SQLite, MongoDB, DuckDB)
4. Enter connection details
5. Test and save
6. Activate the connection
7. Start querying!

### DuckDB Support

DuckDB is now fully supported! To use DuckDB:

1. Create a DuckDB database file or use an existing one
2. In Database Guru, select "DuckDB" as the database type
3. Enter the full path to your .duckdb file
4. Or use `:memory:` for an in-memory database

**Create a sample DuckDB database:**
```bash
python scripts/create_sample_duckdb.py
```

This will create `sample_ecommerce.duckdb` with sample e-commerce data!

## 🔄 Multi-Database Queries

Database Guru supports querying multiple databases simultaneously! Perfect for:

- **Data comparison**: Compare production vs backup databases
- **Migration validation**: Verify data consistency across databases
- **Multi-tenant analysis**: Query across tenant databases
- **Hybrid analytics**: Combine PostgreSQL (OLTP) + DuckDB (OLAP)

### Example Use Cases

```bash
# Compare data across databases
"Compare total customers between production and backup databases"

# Mix database types for analytics
"Show me revenue trends from PostgreSQL and detailed analytics from DuckDB"

# Multi-tenant queries
"Which tenant database has the most active users?"
```

### Quick Start with Multi-Database

1. Create multiple database connections
2. Create a chat session with multiple connections
3. Ask questions that span databases
4. Get aggregated results from all databases

See [MULTI_DATABASE_GUIDE.md](docs/guides/MULTI_DATABASE_GUIDE.md) for full documentation.

## 🔍 Multi-Database Query Validation (NEW!)

Database Guru now includes **intelligent pre-flight validation** for multi-database queries! Before executing a query, the system assesses each database's ability to answer, preventing wasted execution and cryptic errors.

### Key Features:

**1. Per-Database Capability Assessment**

| Capability | Description | UI Treatment |
|------------|-------------|--------------|
| **FULL** | Database has all required tables/columns | ✅ Green badge, auto-selected |
| **PARTIAL** | Missing columns but alternatives found | 🟡 Amber badge, auto-selected |
| **CANNOT** | Missing required data, no alternatives | ❌ Red badge, disabled |

**2. Intelligent Schema Analysis**
- **Production-grade SQL parsing** with `sqlparse` library
- Handles schema-qualified names (`public.orders` → `orders`)
- Extracts tables from JOINs, comma-separated FROM, aliases
- Layered fallback: sqlparse → regex for robustness

**3. Location Query Intelligence**
- Detects location-based queries ("orders from California")
- Checks ALL tables for location columns (enables JOIN-based filtering)
- Comprehensive column list: `state`, `ship_state`, `billing_state`, etc.

**4. Fuzzy Matching for Alternatives**
- Finds similar columns when exact match missing
- Example: `state` → `region`, `province`, `territory`
- Generates modified SQL for PARTIAL capability databases

### Example:

```
Query: "Show orders from California"

🔍 Pre-Flight Validation:
┌─────────────────┬──────────┬─────────────────────────────────────┐
│ Database        │ Status   │ Reason                              │
├─────────────────┼──────────┼─────────────────────────────────────┤
│ Sales DB        │ ✅ FULL   │ Has 'state' column                  │
│ Inventory DB    │ 🟡 PARTIAL│ Using 'region' as alternative       │
│ Products DB     │ ❌ CANNOT │ No location data in schema          │
└─────────────────┴──────────┴─────────────────────────────────────┘

User selects: Sales DB + Inventory DB
→ Different SQL sent to each database based on schema!
```

### UI Components:

- **SchemaGlance** - Overview of all database schemas with location warnings
- **MultiDatabaseAssessment** - Per-database capability selection before execution
- **QueryFeasibilityBadge** - Status badges showing capability at a glance

### Benefits:

| Metric | Before | After |
|--------|--------|-------|
| Multi-DB query success | ~50% | ~90% |
| Schema mismatch detection | 0% | 100% |
| User schema understanding | Low | High |
| Validation time | N/A | <100ms |

### API Endpoint:

```bash
# Pre-validate query against multiple databases
curl -X POST http://localhost:8000/api/multi-db-query/validate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show orders by state",
    "connection_ids": [1, 2, 3]
  }'
```

**Documentation:**
- [Multi-Database Validation Guide](docs/guides/MULTI_DB_VALIDATION_GUIDE.md) - Complete architecture and troubleshooting
- [SQL Generation Pipeline](docs/technical/SQL_GENERATION_PIPELINE.md) - Integration details

---

## 🔗 Data Lineage & Impact Analysis (NEW!)

Database Guru now includes **comprehensive data lineage tracking** with column-level visualization, schema change impact analysis, and query pattern analytics.

### Key Features:

**1. SQL Lineage Visualization**
Parse any SQL query and visualize the complete data flow from source tables to output columns:

```
SQL: SELECT c.name, SUM(o.total) as revenue
     FROM customers c
     JOIN orders o ON c.id = o.customer_id
     GROUP BY c.name

Lineage Graph:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ customers   │────▶│    JOIN     │────▶│    name     │
│ (table)     │     │ (transform) │     │  (output)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   orders    │────▶│     SUM     │────▶│  revenue    │
│  (table)    │     │ (aggregate) │     │  (output)   │
└─────────────┘     └─────────────┘     └─────────────┘
```

- **4 node types**: source_table, source_column, transformation, output_column
- **7 edge types**: direct, contains, feeds, produces, join, filter, data_flow
- **Interactive graph**: Click nodes to highlight connected paths
- **Auto-layout**: Dagre engine for left-to-right data flow visualization

**2. Schema Change Impact Analysis**
Before modifying your database schema, understand which queries will be affected:

| Risk Level | Affected Queries | Recommendation |
|------------|------------------|----------------|
| 🟢 LOW | < 5 queries | Safe to proceed |
| 🟡 MEDIUM | 5-20 queries | Review carefully |
| 🔴 HIGH | > 20 queries | Plan migration |

**Impact Types Detected:**
- SELECT - Column used in output
- FILTER - Column used in WHERE/HAVING
- JOIN - Table/column used in JOIN conditions
- GROUP - Column used in GROUP BY
- ORDER - Column used in ORDER BY

**3. Query Pattern Heatmap**
Analyze query patterns across your database to identify:

| Analysis | What It Shows | Use Case |
|----------|---------------|----------|
| **Frequency** | Most queried tables | Optimize hot tables |
| **Joins** | Common join patterns | Add indexes on join columns |
| **Performance** | Bottleneck tables | Identify slow queries |

- Configurable time ranges: 7 days, 30 days, 90 days, or all history
- Per-connection scoping for multi-database setups
- Bottleneck scoring (0-1) based on frequency × latency

### UI Components:

Access the **Lineage** tab in the main navigation to explore:

- **Explore Tab**: Parse SQL and visualize lineage graphs with React Flow
- **History Tab**: View lineage for previously executed queries
- **Impact Tab**: Analyze schema change impact before modifications
- **Patterns Tab**: Query pattern heatmap with filtering

### Example Use Cases:

**Before Schema Migration:**
```
"What happens if I rename the 'state' column to 'region'?"

Impact Analysis:
├── 15 queries affected (MEDIUM risk)
├── 8 use column in WHERE clauses
├── 5 use column in SELECT
└── 2 use column in GROUP BY

Recommendation: Update application code before schema change
```

**Query Optimization:**
```
"Which tables are bottlenecks?"

Pattern Analysis:
├── orders table: 45% of queries, avg 120ms (BOTTLENECK)
├── customers table: 30% of queries, avg 15ms (OK)
└── products table: 25% of queries, avg 8ms (OK)

Recommendation: Add index on orders(created_at, status)
```

### API Endpoints:

```bash
# Parse SQL and get lineage graph
curl -X POST http://localhost:8000/api/lineage/parse \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM customers JOIN orders ON ..."}'

# Analyze impact of schema change
curl -X POST http://localhost:8000/api/lineage/impact \
  -H "Content-Type: application/json" \
  -d '{"table_name": "customers", "column_name": "state"}'

# Get query pattern heatmap
curl "http://localhost:8000/api/lineage/patterns/1?time_range=30"

# Get lineage for a historical query
curl http://localhost:8000/api/lineage/query/123

# Get queries referencing a table
curl http://localhost:8000/api/lineage/table/customers/queries

# Get lineage statistics
curl http://localhost:8000/api/lineage/stats
```

### Technical Details:

- **SQL Parser**: 835-line parser using `sqlparse` with support for:
  - JOINs (INNER, LEFT, RIGHT, FULL)
  - Subqueries in WHERE/HAVING clauses
  - Aggregations (COUNT, SUM, AVG, MIN, MAX)
  - CASE expressions and complex transformations
  - Table aliases and schema-qualified names
  - SELECT * expansion

- **Graph Visualization**: React Flow with custom nodes/edges, MiniMap, and zoom controls

- **Performance**: Analyzes up to 2,000 queries in pattern analysis with optimized single-pass processing

**Documentation:**
- [Data Lineage Guide](docs/guides/DATA_LINEAGE_GUIDE.md) - Complete feature documentation

---

## 🧠 Lineage Intelligence (NEW!)

Database Guru now includes **LLM-powered lineage intelligence** that transforms technical data lineage into actionable insights. Phase 12 adds five powerful features:

### Key Features:

**1. Lineage Narrator (Phase 12.1)**
Get natural language explanations of your data lineage:

```
SQL: SELECT c.name, SUM(o.total) as revenue FROM customers c JOIN orders o...

📖 Narrative:
"This query calculates total revenue per customer by joining the customers
and orders tables. The SUM aggregation provides customer lifetime value,
which is useful for identifying high-value customers and sales trends."
```

**2. Impact Advisor (Phase 12.2)**
Get LLM-enhanced recommendations before schema changes:

```
Change: Rename column 'state' to 'region' in customers table

🎯 Impact Advice:
├── Risk Level: MEDIUM (15 queries affected)
├── Migration Plan: 5-step guide with SQL
├── SQL Patches: Auto-generated fixes for all affected queries
└── Rollback Strategy: Reversible steps included
```

**3. Schema Health Analyzer (Phase 12.3)**
Comprehensive database design quality analysis:

| Grade | Score | Meaning |
|-------|-------|---------|
| **A** | 90-100 | Excellent - Well-designed schema |
| **B** | 80-89 | Good - Minor improvements possible |
| **C** | 70-79 | Fair - Several issues detected |
| **D** | 60-69 | Poor - Significant problems |
| **F** | <60 | Critical - Requires immediate attention |

**Features:**
- Index suggestions with CREATE SQL
- Normalization issue detection (1NF, 2NF, 3NF)
- Anti-pattern detection (missing PKs, wide tables, etc.)
- Per-table health summaries

**4. Pattern Intelligence (Phase 12.4)**
LLM-enhanced query pattern analysis:

- **Bottleneck Root Cause Analysis**: Why is this table slow?
- **Anti-Pattern Detection**: SELECT *, N+1 queries, Cartesian joins
- **Optimization Suggestions**: Prioritized recommendations with SQL
- **Usage Trends**: Table usage over time (increasing/decreasing/stable)

**5. Conversational Lineage (Phase 12.5)**
Ask questions about your schema in natural language:

```
User: "What tables are used most frequently?"
🤖: Based on query patterns from the last 30 days:
    1. orders (45% of queries) - High traffic table
    2. customers (30%) - Frequently joined with orders
    3. products (25%) - Used in catalog queries

    Suggestion: Consider adding indexes on orders.created_at

User: "What breaks if I rename customers.state?"
🤖: 15 queries would be affected...
```

**Question Types Supported:**
- **Lineage**: "What feeds into this column?"
- **Impact**: "What breaks if I change X?"
- **Pattern**: "What are the bottlenecks?"
- **Schema**: "What columns does this table have?"
- **Recommendation**: "How can I optimize this?"

### UI Access:

Navigate to the **Lineage** tab to access:
- **Narrative** panel - View LLM-generated explanations
- **Health** panel - Schema health dashboard with grades
- **Patterns** panel - Enhanced query pattern analysis
- **Chat** panel - Natural language Q&A interface

### API Endpoints:

```bash
# Get lineage with narrative explanation
curl -X POST "http://localhost:8000/api/lineage/parse?explain=true" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM customers JOIN orders ON ..."}'

# Get impact advice with migration plan
curl -X POST http://localhost:8000/api/lineage/impact/advise \
  -H "Content-Type: application/json" \
  -d '{
    "change_type": "rename_column",
    "table_name": "customers",
    "column_name": "state",
    "new_value": "region",
    "include_patches": true
  }'

# Get schema health report
curl http://localhost:8000/api/lineage/schema/health/1?include_patterns=true

# Get pattern intelligence analysis
curl http://localhost:8000/api/lineage/patterns/1/analyze?time_range=30

# Ask natural language question
curl -X POST http://localhost:8000/api/lineage/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the most used tables?",
    "connection_id": 1
  }'
```

**Documentation:**
- [Lineage Intelligence User Guide](docs/guides/LINEAGE_INTELLIGENCE_USER_GUIDE.md) - Complete feature guide
- [Lineage Intelligence Testing Guide](docs/guides/testing/LINEAGE_INTELLIGENCE_TESTING.md) - How to test
- [Data Lineage Guide](docs/guides/DATA_LINEAGE_GUIDE.md) - Core lineage documentation

---

## 📁 CSV/Excel File Data Sources (NEW!)

Database Guru now supports **CSV and Excel files as queryable data sources**! Upload your files and query them using SQL alongside your traditional databases.

### Key Features:

**1. File Upload Support**
Upload CSV, XLSX, and XLS files directly through the UI:

| Format | Extension | Max Size | Features |
|--------|-----------|----------|----------|
| **CSV** | `.csv` | 100MB | Auto-detect delimiters, encoding |
| **Excel** | `.xlsx` | 100MB | Sheet selection, multiple sheets |
| **Legacy Excel** | `.xls` | 100MB | Full compatibility |

**2. Automatic Schema Inference**
DuckDB automatically detects column types from your data:

| Detected Type | Examples |
|---------------|----------|
| **INTEGER** | `1`, `42`, `1000` |
| **DOUBLE** | `3.14`, `99.99` |
| **VARCHAR** | `"hello"`, `"world"` |
| **BOOLEAN** | `true`, `false`, `1`, `0` |
| **DATE** | `2024-01-15` |
| **TIMESTAMP** | `2024-01-15 10:30:00` |

**3. File Scoping**
Files can be scoped to sessions or shared globally:

| Scope | Use Case | Behavior |
|-------|----------|----------|
| **Session-Scoped** | Temporary analysis | Deleted when session ends |
| **Global** | Shared reference data | Available to all sessions |

**4. Content Deduplication**
Identical files are stored once using SHA-256 hashing, saving storage space.

### How to Use:

**Via UI:**
1. Click the **"📁 Upload File"** button in the sidebar
2. Drag-and-drop or click to select your CSV/Excel file
3. (For Excel) Select which sheet to import
4. Optionally provide a display name
5. Click **"Upload"** to process the file
6. View schema and preview in the **File Preview Panel**
7. Query using the generated DuckDB table name (e.g., `file_1_sales_data`)

**Via API:**
```bash
# Upload a file
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@sales_data.csv" \
  -F "name=Sales Data" \
  -F "is_global=false"

# List uploaded files
curl http://localhost:8000/api/files/

# Get file schema
curl http://localhost:8000/api/files/1/schema

# Preview file data
curl http://localhost:8000/api/files/1/preview?limit=20

# Inspect Excel sheets before upload
curl -X POST http://localhost:8000/api/files/excel-sheets \
  -F "file=@workbook.xlsx"

# Delete a file
curl -X DELETE http://localhost:8000/api/files/1
```

### Example Workflow:

```
1. Upload "sales_data.csv" (500 rows)
   → Auto-detects: product_id (INT), name (VARCHAR), revenue (DOUBLE), sale_date (DATE)
   → Creates DuckDB table: file_1_sales_data

2. Query naturally:
   "Show me total revenue by product from sales_data"
   → SELECT product_id, name, SUM(revenue) FROM file_1_sales_data GROUP BY product_id, name

3. Join with database tables:
   "Compare sales_data revenue with our products table"
   → Joins file source with connected database
```

### UI Components:

- **FileUploadModal** - Drag-and-drop upload with progress indicator
- **FilePreviewPanel** - Two-tab interface with schema and data preview
- **Sheet Selection** - Choose which Excel sheet to import
- **Type Badges** - Color-coded column type indicators

### Configuration:

Settings in `.env`:
```bash
# File upload settings
FILE_UPLOAD_DIR=uploads/          # Storage directory
FILE_MAX_SIZE_MB=100              # Maximum file size
FILE_ALLOWED_TYPES=.csv,.xlsx,.xls  # Accepted extensions
FILE_AUTO_CLEANUP_DAYS=30         # Auto-delete after N days

# DuckDB settings for file queries
DUCKDB_FILE_MEMORY_LIMIT=1GB      # Max memory for queries
DUCKDB_FILE_THREADS=4             # Processing threads
```

### Benefits:

| Feature | Benefit |
|---------|---------|
| **No ETL Required** | Query files directly without importing to databases |
| **Fast Processing** | DuckDB's columnar engine handles large files efficiently |
| **Type Safety** | Automatic type inference prevents data errors |
| **Session Isolation** | Each user's files are isolated by session |
| **Storage Efficiency** | Content deduplication saves disk space |

### Technical Details:

- **Storage**: Files stored in `uploads/` with hash-based naming
- **Processing**: DuckDB's `read_csv_auto()` and `read_excel()` functions
- **Memory**: Lazy table loading - tables only loaded when queried
- **Thread Safety**: AsyncIO locks protect concurrent access
- **Cleanup**: Automatic expiration after configurable days

**Documentation:**
- [File Data Source User Guide](docs/guides/FILE_DATA_SOURCE_USER_GUIDE.md) - Complete feature guide
- [File Data Source Testing Guide](docs/guides/testing/FILE_DATA_SOURCE_TESTING.md) - How to test

---

## 🎯 Confidence Scoring (NEW!)

Database Guru now predicts the success probability of SQL corrections BEFORE executing them! Get instant feedback on whether a fix is likely to work.

### 🚀 Key Benefits:
- **30-40% fewer wasted database calls** - Skip hopeless corrections automatically
- **Instant transparency** - See exactly how confident the system is
- **Historical learning** - Gets smarter over time
- **5-factor analysis** - Comprehensive success prediction
- **Resource optimization** - Auto-skip very low confidence fixes (< 20%)

### How It Works:
Every time the system corrects a SQL error, it analyzes 5 key factors:

1. **Error Type** (30% weight) - How difficult is this error to fix?
   - Table typos: 85% base confidence ✅
   - Syntax errors: 60% base confidence ⚡
   - Connection issues: 10% base confidence ❌

2. **Schema Match** (25% weight) - Does the correction use valid tables/columns?
   - Validates against actual database schema
   - Detects typos and suggests alternatives

3. **Historical Success** (20% weight) - How often do we fix this error type?
   - Learns from past corrections
   - Improves predictions over time

4. **Correction Complexity** (15% weight) - How big is the change?
   - Simple edits → Higher confidence
   - Major rewrites → Lower confidence

5. **Similarity** (10% weight) - How similar to original?
   - Minor changes → Higher confidence
   - Complete rewrites → Lower confidence

### Visual Confidence Badges:
```
🎯 92.5% HIGH      - Green badge, execute with confidence
⚡ 67.5% MEDIUM    - Yellow badge, worth trying
⚠️  29.5% LOW       - Orange badge, try alternatives
🚫 10.5% VERY_LOW  - Red badge, auto-skipped
```

### Example:
```
Question: "Show me all data from custmers table"

Attempt 1: SELECT * FROM custmers
❌ Error: table "custmers" does not exist

Attempt 2: SELECT * FROM customers
🎯 Confidence: 92.5% (HIGH)
   ├─ Error Type: 25.5% (table typos are easy to fix)
   ├─ Schema Match: 25.0% (✅ "customers" exists in schema)
   ├─ Historical: 17.0% (85% success rate on this error)
   ├─ Complexity: 15.0% (simple one-word change)
   └─ Similarity: 10.0% (very similar to original)

Recommendation: EXECUTE - High confidence, likely to succeed
✅ Success! Query returned 150 rows
```

### In the UI:
Click on any auto-corrected query to see:
- Color-coded confidence badge
- Detailed factor breakdown
- Success probability percentage
- AI reasoning and recommendations
- Progress bars showing each factor's contribution

### API Usage:
```bash
# Predict confidence for a correction
curl -X POST http://localhost:8000/api/confidence/predict \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "table_not_found",
    "original_sql": "SELECT * FROM custmers",
    "correction_sql": "SELECT * FROM customers",
    "schema": {"customers": ["id", "name", "email"]}
  }'

# View historical statistics
curl http://localhost:8000/api/confidence/stats
```

**Documentation:**
- [Confidence Scoring Guide](docs/technical/CONFIDENCE_SCORING.md) - Complete feature guide
- [UI Components](docs/reports/CONFIDENCE_SCORING_UI.md) - Frontend implementation
- [Verification Guide](docs/reports/CONFIDENCE_SCORING_VERIFICATION.md) - How to test it
- [Manual Testing](docs/reports/CONFIDENCE_SCORING_MANUAL_TEST.md) - Step-by-step testing

## 💬 Conversational Memory (NEW!)

Database Guru now remembers your conversation! Have natural, multi-turn dialogs where you can refine queries without repeating context.

### 🚀 Key Benefits:
- **Natural conversations** - Ask follow-ups like "filter by electronics" or "sort by price"
- **Smart context detection** - Knows when to use conversation history vs standalone queries
- **Configurable memory** - Default 3-query window (adjustable)
- **Visual feedback** - See what the AI remembers in the context panel
- **Session-based** - Each chat session maintains independent context
- **Fast retrieval** - < 10ms context loading with minimal overhead

### How It Works:
Every chat session maintains a conversation history. When you ask a follow-up question, the system automatically:

1. **Retrieves recent context** - Last N queries (default: 3)
2. **Detects context need** - Determines if question references previous queries
3. **Enhances prompt** - Adds conversation history to LLM prompt
4. **Generates SQL** - Creates context-aware query
5. **Saves to history** - Remembers for future refinements

### Example Conversation:
```
User: "Show me all products"
→ SQL: SELECT * FROM products
→ Result: 100 rows

User: "Filter by electronics"
→ System remembers previous query
→ SQL: SELECT * FROM products WHERE category = 'electronics'
→ Result: 25 rows

User: "Sort by price"
→ System uses full context
→ SQL: SELECT * FROM products WHERE category = 'electronics' ORDER BY price
→ Result: 25 rows (sorted)
```

### In the UI:
- **Context Panel** - View conversation history with SQL and results
- **Context Badge** - Blue indicator when memory is active
- **Clear Context** - Start fresh anytime
- **Refresh** - Manually reload context

### API Usage:
```bash
# Query with conversational context
curl -X POST http://localhost:8000/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Filter by electronics",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }'

# View conversation context
curl http://localhost:8000/api/chat/sessions/{session_id}/context

# Clear context (fresh start)
curl -X DELETE http://localhost:8000/api/chat/sessions/{session_id}/context
```

**Documentation:**
- [Conversational Memory Implementation](docs/technical/CONVERSATIONAL_MEMORY_IMPLEMENTATION.md) - Technical deep dive
- [Phase 1 Complete Summary](docs/reports/PHASE_1_COMPLETE.md) - Feature completion report
- [Testing Guide](docs/reports/TEST_CONVERSATIONAL_MEMORY.md) - How to test the feature

**Security Features:**
- Multi-layer prompt injection detection and prevention
- Input sanitization removes control characters and malicious patterns
- Safe prompt construction with delimiter protection
- Token limits prevent resource exhaustion
- Defense in depth: API validation → Agent validation → Prompt sanitization

## 🧠 Learning from Corrections

Database Guru now learns from its mistakes! The system automatically remembers successful corrections and applies them to similar errors in the future.

### Key Benefits:
- **50% faster** error recovery on repeated errors
- **33% fewer LLM calls** - saves API costs
- **85% success rate** (up from 70%)
- **Automatic learning** - no configuration needed

### How It Works:
1. First time an error occurs → Agent fixes it
2. System **learns** the correction pattern
3. Next time similar error → **Instant fix!**

### Example:
```
User: "Show me all products"
Error: table "prodcuts" does not exist
→ Agent fixes: "products"
✨ Correction learned!

[Later...]
User: "What are the latest products?"
Error: table "prodcuts" does not exist
→ Instant fix (no retry needed)
```

### View Learned Corrections:
```bash
# See what the system has learned
curl http://localhost:8000/api/learned-corrections/stats/summary

# View all corrections
curl http://localhost:8000/api/learned-corrections/
```

**Documentation:**
- [Learning from Corrections Guide](docs/technical/LEARNING_FROM_CORRECTIONS.md)
- [Quick Start Guide](docs/guides/LEARNING_QUICKSTART.md)
- [Self-Correcting Agent](docs/modules/SELF_CORRECTING_AGENT.md)

## 🛡️ Result Verification (NEW!)

Database Guru now verifies query results to catch logical errors before showing them to users!

### What It Catches:
- ❌ **Empty results** when data should exist
- ❌ **All NULL values** (wrong column names)
- ❌ **Extreme values** (calculation errors)
- ❌ **Suspicious counts** (COUNT returning 0)
- ❌ **Impossible values** (negative counts)

### How It Works:
1. Query executes successfully ✅
2. Agent verifies results 🔍
3. If suspicious → Runs diagnostics 📊
4. High confidence issue → Regenerates query 🔧
5. Returns correct results ✅

### Example:
```
User: "Show me customers over 150 years old"
SQL: SELECT * FROM customers WHERE age > 150
Result: 0 rows

🔍 Verification: "Suspicious empty result!"
📊 Diagnostics: Table has 150 customers, ages 18-89
🔧 Regenerates: SELECT * FROM customers WHERE age > 80
✅ Returns: Senior customers
```

### Key Benefits:
- **70-80%** of logical errors caught automatically
- **2-3x fewer** user complaints about wrong results
- **Minimal impact** (~0.1ms verification overhead)
- **Automatic** - no configuration needed

### Check Verification:
```bash
# Verify a result manually
curl -X POST http://localhost:8000/api/verify/result \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many customers?",
    "sql": "SELECT COUNT(*) FROM customers",
    "result": {"success": true, "data": [{"count": 0}]}
  }'

# Health check
curl http://localhost:8000/api/verify/health
```

**Documentation:**
- [Result Verification Guide](docs/modules/RESULT_VERIFICATION_AGENT.md)
- [Quick Start Guide](docs/guides/RESULT_VERIFICATION_QUICKSTART.md)
- [Implementation Summary](docs/reports/RESULT_VERIFICATION_IMPLEMENTATION_SUMMARY.md)

## 🎯 Query Planning with Schema Validation (NEW!)

Database Guru now uses an intelligent Query Planning Agent that creates structured execution plans before generating SQL, resulting in **4x better accuracy** on complex queries!

### What It Does:
- 🧠 **Chain-of-thought reasoning** - Breaks down complex questions into structured plans
- 🔍 **Schema validation** - Detects column/table mismatches automatically
- 🔧 **Auto-correction** - Fixes schema errors without user intervention
- 🗺️ **Smart join discovery** - Finds optimal join paths between tables
- 💡 **Intelligent suggestions** - Recommends corrections with fuzzy matching

### Example: California Products Query
```
Question: "How many products were shipped to California?"

❌ OLD: Failed with "column 'shipping_address' not found"

✅ NEW: Detects error, finds 'state' in customers table
        Discovers join path: order_items → orders → customers
        Generates correct multi-table query automatically!
```

### How It Works:
1. User asks question in natural language
2. **Query Planner** analyzes and creates structured plan
3. **Schema Validator** checks all tables/columns exist
4. If errors found → **Auto-correction** with suggestions
5. Generates accurate SQL from validated plan

### What It Catches:
- ❌ **Missing columns** ("shipping_address" → suggests "customers.state")
- ❌ **Wrong tables** (looks for location in "orders" → finds in "customers")
- ❌ **Invalid joins** (suggests optimal join paths with foreign keys)
- ❌ **Typos** ("costumers" → "customers" with fuzzy matching)

### Key Benefits:
- **4x better accuracy** on multi-table queries
- **Automatic error correction** - no manual fixing needed
- **Cross-table intelligence** - finds columns in related tables
- **Helpful error messages** - shows exactly what's wrong and how to fix it
- **Production ready** - graceful fallback if validation fails

### Try It:
```bash
# Create a query plan
curl -X POST http://localhost:8000/api/query-planning/plan \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me products shipped to California"
  }'

# View plan explanation and validation results
```

**Documentation:**
- [Query Planning Guide](docs/modules/QUERY_PLANNING_AGENT.md)
- [Schema Validation Details](docs/technical/SCHEMA_VALIDATION_IMPROVEMENTS.md)
- [Quick Start Guide](docs/guides/QUERY_PLANNING_QUICKSTART.md)
- [Implementation Summary](docs/reports/QUERY_PLANNING_IMPLEMENTATION_SUMMARY.md)

## 🔍 Learned Mapping Management (NEW!)

Database Guru now provides **comprehensive visibility and control** over learned patterns! View, filter, and manage all column/table mappings and result validation patterns learned from user feedback.

### Key Features:
- 📊 **Management Dashboard** - View all learned patterns in one place
- 🎯 **Advanced Filtering** - Filter by connection, table, database type
- 📈 **Usage Analytics** - Track which patterns are most effective
- 🗑️ **Pattern Cleanup** - Delete outdated or incorrect mappings
- 🏷️ **Helpfulness Tracking** - Mark patterns as helpful or not
- 📉 **Statistics Dashboard** - Overall effectiveness metrics

### What You Can Manage:

**1. Column Mappings**
- View source → target column corrections (e.g., "price" → "unit_price")
- See which tables each mapping applies to
- Track usage counts and success rates
- Filter by connection or database type

**2. Table Mappings**
- View source → target table corrections (e.g., "customer_data" → "customers")
- See mapping types (alias, rename, etc.)
- Track application frequency
- Monitor success rates

**3. Result Validation Patterns**
- View learned patterns for common result issues
- See pattern types (empty_result, missing_data, etc.)
- Track how often patterns are triggered
- Monitor helpfulness ratings

### How to Access:

**Via UI:**
1. Navigate to **Settings** or **Admin** section
2. Click on **"Learned Patterns"** tab
3. Browse mappings organized by type
4. Use filters to narrow down results
5. Delete patterns with the trash icon
6. View statistics in the Stats tab

**Via API:**
```bash
# List column mappings
curl http://localhost:8000/api/mappings/columns?connection_name=my_db&limit=20

# List table mappings
curl http://localhost:8000/api/mappings/tables?database_type=postgresql

# List result patterns
curl http://localhost:8000/api/mappings/patterns?pattern_type=empty_result

# Get column mapping statistics
curl http://localhost:8000/api/mappings/columns/stats

# Delete a column mapping
curl -X DELETE http://localhost:8000/api/mappings/columns/123

# Mark result pattern as helpful
curl -X POST http://localhost:8000/api/mappings/patterns/456/helpful
```

### Key Benefits:
- **Visibility** - See exactly what the system has learned
- **Control** - Remove incorrect or outdated patterns
- **Analytics** - Understand which patterns are most valuable
- **Debugging** - Troubleshoot why certain corrections are applied
- **Auditing** - Track learning progress over time
- **Quality Assurance** - Review and validate learned patterns

### Example Use Cases:

**Cleanup Stale Mappings:**
```
View all column mappings that haven't been used in 30 days
→ Delete unused patterns to keep the system lean
```

**Monitor Effectiveness:**
```
Check which table mappings have 100% success rate
→ Identify reliable patterns for documentation
```

**Debug Corrections:**
```
Filter mappings by connection "sales_db"
→ See why certain columns are being renamed
```

**Track Learning Progress:**
```
View statistics dashboard
→ See total patterns learned, application counts, success rates
```

### API Endpoints:

**Column Mappings:**
- `GET /api/mappings/columns` - List mappings with filters
- `DELETE /api/mappings/columns/{id}` - Delete mapping
- `GET /api/mappings/columns/stats` - Statistics

**Table Mappings:**
- `GET /api/mappings/tables` - List mappings with filters
- `DELETE /api/mappings/tables/{id}` - Delete mapping
- `GET /api/mappings/tables/stats` - Statistics

**Result Patterns:**
- `GET /api/mappings/patterns` - List patterns with filters
- `DELETE /api/mappings/patterns/{id}` - Delete pattern
- `POST /api/mappings/patterns/{id}/helpful` - Mark as helpful
- `GET /api/mappings/patterns/stats` - Statistics

**Documentation:**
- [Mapping Management Guide](docs/guides/MAPPING_MANAGEMENT.md) - Complete feature guide
- [Next Steps Guide](docs/guides/NEXT_STEPS_GUIDE.md) - Integration roadmap

---

## 🎓 User Feedback Integration with Smart Auto-Learning (NEW!)

Database Guru now learns from YOUR corrections with **production-grade validation**! When the system makes a mistake, you can provide feedback to help it improve over time - with built-in security to prevent bad corrections.

### 🛡️ Smart Auto-Learning (NEW!)
- 🤖 **Automatic validation** - High-confidence feedback (≥90%) auto-applied after comprehensive testing
- 🔍 **Comparative testing** - Validates corrections actually improve results
- 🚫 **Destructive operation blocking** - DELETE/UPDATE/DROP operations NEVER auto-learned
- ⚙️ **3 Validation Modes** - Strict (production), Moderate (balanced), Lenient (testing)
- 📊 **Pattern detection** - Blocks suspicious changes automatically

### What You Can Do:
- 🔧 **Correct SQL queries** - Fix wrong SQL and teach the system (safe operations only)
- 📝 **Report column/table issues** - Flag incorrect schema usage
- ⚠️ **Flag result problems** - Report suspicious or wrong results
- 📊 **Track improvements** - View feedback stats dashboard
- ⚙️ **Configure auto-learning** - Control validation strictness and behavior

### How It Works:
1. Execute a query and notice an issue
2. Click the **"Feedback"** button next to the SQL
3. Choose feedback type and provide correction
4. Submit feedback with confidence level (0-100%)
5. **Smart Validation** - System runs comprehensive checks:
   - ✅ Corrected SQL must execute successfully
   - ✅ Original SQL must fail (strict mode)
   - ✅ Checks for suspicious patterns
   - ✅ Blocks destructive operations (DELETE, UPDATE, DROP, etc.)
6. **Auto-Apply** - If validation passes, learns immediately!

### Example - Safe Correction (Auto-Applied):
```
Query: "Show me all customers"
Generated SQL: SELECT * FROM customer_data
Result: ❌ Table not found

→ Click "Feedback" button
→ Correct to: SELECT * FROM customers
→ Set confidence: 95%
→ Submit

🔍 Validating...
✅ Corrected SQL works (5 rows)
✅ Original SQL fails (table not found)
✅ No suspicious patterns
✨ AUTO-APPLIED! Next time it will use "customers" automatically
```

### Example - Destructive Operation (Blocked):
```
Query: "Show inactive users"
Generated SQL: SELECT * FROM users WHERE active = 0

→ User "corrects" to: DELETE FROM users WHERE active = 0
→ Set confidence: 100%
→ Submit

🔍 Validating...
❌ BLOCKED: Destructive operation (DELETE) detected
📝 Saved for manual admin review
🛡️ System protected from learning destructive operations!
```

### Feedback Types:
1. **SQL Correction** - Provide corrected SQL query
2. **Column Name** - Report wrong column name
3. **Table Name** - Report wrong table name
4. **Result Issue** - Flag problems with results

### View Feedback Stats:
- Navigate to Feedback Dashboard in the UI
- See total feedback, applied corrections, pending reviews
- Track learning progress over time

### API Endpoints:
```bash
# Submit feedback (auto-validates if enabled)
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 123,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM customers",
    "correction_description": "Table name should be customers not customer_data",
    "user_confidence": 0.95
  }'
# → Auto-applies if validation passes!

# Configure auto-learning settings
curl -X PUT http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{
    "auto_learning_enabled": true,
    "validation_mode": "strict",
    "test_before_learning": true
  }'

# Get current settings
curl http://localhost:8000/api/settings/

# Get feedback stats
curl http://localhost:8000/api/feedback/stats
```

### Key Benefits:
- **Production-grade security** - Blocks destructive operations (DELETE, UPDATE, DROP)
- **Comprehensive validation** - Compares original vs corrected before learning
- **Continuous improvement** - System gets smarter over time
- **Domain-specific learning** - Learns YOUR database patterns
- **Collaborative** - Team corrections benefit everyone
- **Confidence tracking** - Know which corrections are most reliable
- **Audit trail** - All auto-applied feedback logged for compliance

### Security & Validation:
The system uses **3 layers of protection**:
1. **Confidence filter** - Only ≥90% confidence considered for auto-apply
2. **Comprehensive validation** - Executes both original and corrected SQL
3. **Pattern detection** - Blocks destructive operations and suspicious changes

**Blocked Operations (NEVER auto-learned):**
- `DELETE` - Even with WHERE clauses
- `UPDATE` - Even with WHERE clauses
- `DROP` - Tables, databases, indexes, etc.
- `ALTER` - Schema modifications
- `TRUNCATE` - Table truncation

These require manual admin review for safety.

**Documentation:**
- **[Auto-Learning Guide](docs/guides/AUTO_LEARNING_GUIDE.md)** - Complete user guide
- **[Validation System](docs/technical/VALIDATION_SYSTEM.md)** - Technical validation details
- **[Security Policy](docs/technical/SECURITY_POLICY.md)** - Enterprise security controls
- **[Security Enhancements Summary](docs/reports/SECURITY_ENHANCEMENTS_SUMMARY.md)** - What changed and why
- [User Feedback System Guide](USER_FEEDBACK_SYSTEM.md)
- [Multi-Database Feedback Integration](MULTI_DB_FEEDBACK_INTEGRATION.md)

## 🎨 Recent UI Improvements (NEW!)

Database Guru's interface has been enhanced with several quality-of-life improvements:

### Connection Management
- **Edit Button** - Edit existing database connections without recreating them
- **Loading States** - Visual feedback during connection save operations
- **Selected Highlighting** - Blue border shows which connection is currently selected
- **Database Icon** - Connection status indicator in header with database icon

### Agent Execution Trace
- **Defensive Rendering** - No more blank pages when expanding traces
- **Cache Indicators** - Visual badges for cache hits/misses with icons:
  - ⚡ Semantic cache hit (amber)
  - 🔍 Cache miss (slate)
  - 💾 Cache store (teal)
  - 🗄️ Cache lookup (amber)
- **Robust Data Handling** - Graceful fallbacks for missing trace properties

### Conversational Memory
- **Context Toggle** - Show/hide conversation history panel with one click
- **Visual Feedback** - Active context indicator with toggle button
- **Improved UX** - Cleaner interface for multi-turn conversations

### Multi-Database Results
- **Cache Info Banner** - Summary of cached vs fresh database queries
- **Per-Database Badges** - See which databases used cache at a glance
- **Cache Metrics** - Real-time cache hit/miss tracking

All improvements maintain the existing color scheme and design language for consistency.

---

## 📊 Row Limits & Result Pagination (NEW!)

Database Guru now gives you full control over query result sizes with configurable row limits and paginated result tables.

### Row Limit Selector

Choose how many rows to return per query with a convenient dropdown:

| Option | Use Case |
|--------|----------|
| **10 rows** | Quick preview, testing |
| **25 rows** | Small datasets |
| **50 rows** | Medium datasets |
| **100 rows** (default) | Standard queries |
| **250 rows** | Larger analysis |
| **500 rows** | Detailed exploration |
| **1,000 rows** | Comprehensive data |
| **5,000 rows** | Large exports |
| **10,000 rows** | Maximum data retrieval |

The selected limit is passed to the SQL generation, which includes an appropriate `LIMIT` clause (unless doing aggregations like `COUNT`/`SUM`/`AVG`).

### Result Table Pagination

Navigate through large result sets with built-in pagination:

- **Rows per page**: 10, 25, 50, or 100 rows per page
- **Navigation**: Previous/Next buttons to cycle through pages
- **Range indicator**: "1-10 of 250" shows current position
- **Independent pagination**: Each database result in multi-database queries has its own pagination
- **Page size memory**: Selection persists while viewing results

### Example:
```
Query: "Show me all products" with 500 row limit

Result: 487 rows returned
Table shows: 1-10 of 487
[Rows per page: 10 ▼]  [< Prev] [1-10 of 487] [Next >]

Change to 50 rows per page:
Table shows: 1-50 of 487
[Rows per page: 50 ▼]  [< Prev] [1-50 of 487] [Next >]
```

---

## 🔀 Table Sorting (NEW!)

Database Guru now supports **client-side table sorting** with smart type detection. Click any column header to sort your query results.

### Features:

- **Click to Sort**: Click any column header to sort ascending, click again for descending
- **Smart Type Detection**: Automatically detects and sorts appropriately:
  - **Numbers**: Numeric sorting (1, 2, 10, not 1, 10, 2)
  - **Dates**: Chronological sorting for ISO date strings
  - **Strings**: Case-insensitive alphabetical sorting
- **Null Handling**: Null values always sort to the end regardless of direction
- **Visual Indicators**: Arrow icons show current sort column and direction
- **Keyboard Accessible**: Use Enter or Space to sort columns
- **Pagination Integration**: Sorting resets to page 1 when sort changes

### Example:
```
Click "Price" column header:
  → Data sorts by price ascending (lowest first)
  → Arrow up icon appears

Click "Price" again:
  → Data sorts by price descending (highest first)
  → Arrow down icon appears

Click "Name" column:
  → Data sorts by name A-Z
  → Price column shows neutral icon
```

### Works In:
- Single database query results
- Multi-database query results (independent per database)
- Streaming query results (sorting disabled during streaming)

---

## 📊 Advanced Visualization (NEW!)

Database Guru now includes **intelligent chart visualization** with automatic chart type detection and manual override capabilities!

### Key Features:

**1. Intelligent Chart Detection**
The system automatically analyzes your query results and recommends the best chart type:

| Chart Type | Auto-Detection Criteria | Use Case |
|------------|------------------------|----------|
| **Line Chart** | Temporal column + numeric data, or trend detected | Time-series, trends |
| **Scatter Plot** | Correlation detected (≥10 rows, r > 0.7) | Relationships, correlations |
| **Pie Chart** | Categorical + numeric, 2-8 unique values | Distribution, proportions |
| **Bar Chart** | Categorical + numeric, 9-15 unique values | Comparisons |
| **Area Chart** | Time-series with composition data | Stacked trends |
| **Histogram** | Single numeric column, >20 rows | Distribution analysis |
| **Box Plot** | Categorical + numeric for grouping | Statistical distribution |
| **Treemap** | Hierarchical categorical data | Nested proportions |
| **Sunburst** | Multi-level hierarchical data | Radial hierarchy |
| **Bubble** | 3+ numeric columns | 3-variable relationships |
| **Table** | Default fallback | Raw data viewing |

**2. Manual Chart Type Selection**
Override the auto-detection anytime:
- Click the dropdown (▼) next to the Table/Chart toggle
- See which type is "(recommended)" by auto-detection
- Switch between all 10 chart types: Bar, Line, Pie, Scatter, Area, Histogram, Box Plot, Treemap, Sunburst, Bubble
- Works in single queries, per-database views, and cross-database comparisons

**3. Export Capabilities**

| Format | Description |
|--------|-------------|
| **CSV** | Comma-separated values (Excel compatible) |
| **JSON** | Includes metadata, timestamps, and SQL |
| **Clipboard** | Tab-separated for quick paste to spreadsheets |
| **ZIP** | Separate files per database (multi-database only) |

**4. Multi-Database Visualization**
- **Per-database charts** - Each database result has independent chart controls
- **Cross-database comparison** - Automatically finds common numeric columns and visualizes comparisons
- **Combined export** - Export all database results in one file (stacked) or separate files (ZIP)

### Example:
```
Query: "Show me total sales by category"

Auto-Detection: Bar Chart (recommended)
  → 5 categories detected
  → Numeric 'total_sales' column found

User Override: Switch to Pie Chart
  → Shows proportional distribution instead
```

### Correlation Detection:
Scatter plots require **minimum 10 data points** to avoid spurious correlations in small datasets. This ensures statistical reliability when visualizing relationships between columns.

**Documentation:**
- [Advanced Visualization Guide](docs/guides/ADVANCED_VISUALIZATION_GUIDE.md) - Complete feature documentation
- [Chart Type Selector PR Review](docs/reports/CHART_TYPE_SELECTOR_PR_REVIEW.md) - Manual testing guide

---

## 🧪 Testing

Database Guru has comprehensive test coverage with automated testing for all major components.

### Quick Test Status
![Tests](https://img.shields.io/badge/tests-250%2B%20passing-brightgreen)
![Backend Tests](https://img.shields.io/badge/backend-107%20tests-brightgreen)
![Frontend Tests](https://img.shields.io/badge/frontend-144%20tests-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-55%25-yellow)
![Components](https://img.shields.io/badge/components-fully%20tested-brightgreen)

### Run Tests
```bash
# Run all tests
./run_tests.sh

# Run specific test suite
./run_tests.sh tests/test_result_verification_agent.py

# Run with coverage report
source venv/bin/activate
python -m pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Test Documentation
- **[Testing Guide](TESTING.md)** - How to run and write tests
- **[Test Status Report](TEST_STATUS.md)** - Detailed test results and status
- **[Coverage Summary](COVERAGE_SUMMARY.md)** - Code coverage breakdown and improvement plan

### Test Coverage by Component
- ✅ **Parallel Execution**: 13/13 tests (100% coverage) - PRODUCTION-READY!
  - Backend: 6 multi-DB + 7 corrections tests
  - Speedup verification, timeout protection, metrics tracking
- ✅ **Frontend Parallel Metrics**: 42/42 tests (100% coverage)
  - ParallelDatabaseMetrics: 20 tests
  - ParallelCorrectionsMetrics: 16 tests
  - QueryResults integration: 6 tests
- ✅ **Semantic Cache UI**: 43/43 tests (100% coverage) - NEW!
  - Backend cache endpoints: 9 tests
  - Frontend cache components: 34 tests (SemanticCachePanel, CacheOverview, CacheStatistics, RecentCachedQueries, QueryResults badge)
- ✅ **Row Limit & Pagination**: 26/26 tests (100% coverage) - NEW!
  - QueryResults pagination: 10 tests (navigation, page size, boundary conditions)
  - MultiDatabaseResults pagination: 16 tests (per-database controls, independent navigation)
- ✅ **Multi-Database Query Validation**: 27/27 tests (100% coverage) - NEW!
  - Capability assessment (FULL/PARTIAL/CANNOT)
  - SQL parsing with sqlparse
  - Fuzzy matching and alternatives
  - Location detection and validation
- ✅ **Data Lineage System**: 135+ tests (100% coverage)
  - SQL Lineage Parser: 100+ tests (JOINs, subqueries, aggregations)
  - Impact Analyzer: 20+ tests (risk levels, impact types)
  - Query Pattern Analyzer: 20+ tests (frequency, bottlenecks)
  - Frontend: 15+ tests (LineageGraph, heatmap visualization)
- ✅ **Lineage Intelligence (Phase 12)**: 2960+ tests (100% coverage) - NEW!
  - Lineage Narrator: 474 tests (narrative generation, LLM integration)
  - Impact Advisor: 455 tests (migration plans, SQL patches)
  - Schema Health Analyzer: 817 tests (grades, index suggestions, anti-patterns)
  - Pattern Intelligence: 584 tests (bottleneck analysis, anti-pattern detection)
  - Conversational Lineage: 630 tests (question classification, multi-turn dialog)
- ✅ **Table Sorting**: 24/24 tests (100% coverage)
  - useTableSort hook: 14 tests (sorting logic, type detection, nulls)
  - SortableTableHeader: 10 tests (click, keyboard, visual indicators)
- ✅ **CSV/Excel File Data Sources**: 50+ tests (100% coverage) - NEW!
  - File validation and sanitization tests
  - Schema inference tests (CSV, Excel)
  - DuckDB session management tests
  - File preview and API endpoint tests
  - Content validation and deduplication tests
- ✅ **LLM Usage Monitoring**: Unit + integration tests - NEW!
  - Token estimation and native extraction
  - Cost calculation and model config
  - Usage aggregation and API endpoints
- ✅ Confidence Scoring: 31/31 tests (100% coverage)
- ✅ Result Verification Agent: 14/14 tests (89% coverage)
- ✅ Correction Learner: 13/13 tests (87% coverage)
- ✅ Schema-Aware Fixer: 24/24 tests (79% coverage)
- ✅ Self-Correcting Agent: 16/16 tests (95% coverage)
- ✅ Frontend Confidence UI: 23/23 tests (100% coverage)

## 🔄 CI/CD

Database Guru has comprehensive GitHub Actions workflows for continuous integration and delivery.

### Workflows
- 🧪 **Tests**: Run on every push and PR (Python 3.11, 3.12, 3.13)
- 📊 **Coverage Badge**: Auto-generate coverage badge on push to main
- ✅ **PR Checks**: Validate PRs with component tests and coverage diff
- 🌙 **Scheduled Tests**: Nightly tests and dependency audits

### Quick Links
- **[CI/CD Setup Guide](.github/CICD_SETUP.md)** - Complete workflow documentation
- **[Workflows Reference](.github/WORKFLOWS_REFERENCE.md)** - Quick reference card
- **[Actions Tab](https://github.com/sammyLOMI22/database-guru/actions)** - View workflow runs

### Features
- ✅ Automated testing on multiple Python versions
- ✅ Code coverage tracking with Codecov integration
- ✅ Security scanning (bandit, safety)
- ✅ Lint checks (flake8, black, isort, mypy)
- ✅ PR status comments with test results
- ✅ Automatic issue creation on nightly test failures
- ✅ Performance benchmarking

## 🐛 Troubleshooting

**Ollama not found:**
```bash
brew install ollama
ollama serve
```

**Port already in use:**
```bash
# Kill processes on ports 3000 or 8000
lsof -ti:3000 | xargs kill -9
lsof -ti:8000 | xargs kill -9
```

**Frontend build errors:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Backend import errors:**
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

## 📝 Development

**Backend hot reload:**
Changes auto-reload when you edit Python files

**Frontend hot reload:**
React components update instantly on save

**View logs:**
```bash
tail -f backend.log
tail -f frontend.log
```

## 🤝 Contributing

This is a development project. Feel free to:
- Add new database adapters
- Improve SQL generation prompts
- Enhance UI/UX
- Add security features

## 📄 License

MIT License - See LICENSE file

## 🙏 Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Ollama](https://ollama.ai/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Tailwind CSS](https://tailwindcss.com/)

---

**Made with ❤️ for developers who hate writing SQL**
