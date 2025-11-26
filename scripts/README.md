# Database Guru Scripts

Helper scripts for Database Guru setup and management.

## Cache Setup Scripts

### `setup_cache.sh` - Complete Cache Setup

Automated setup for both Redis and Ollama with models.

```bash
./scripts/setup_cache.sh
```

**What it does:**
1. Runs Redis setup (installs, starts service)
2. Runs Ollama setup (installs, starts service, pulls models)
3. Provides final configuration instructions

**When to use:** First-time setup or complete cache reconfiguration.

---

### `setup_redis.sh` - Redis Setup

Interactive Redis installation and startup.

```bash
./scripts/setup_redis.sh
```

**Features:**
- ✅ Checks if Redis is installed
- ✅ Offers to install via Homebrew
- ✅ Starts Redis as background service or foreground
- ✅ Verifies Redis is running
- ✅ Provides configuration instructions

**Options:**
- Install Redis if not present
- Start as background service (auto-starts on boot)
- Start in foreground (manual control)
- Skip if already running

---

### `setup_ollama.sh` - Ollama Setup

Interactive Ollama installation and model management.

```bash
./scripts/setup_ollama.sh
```

**Features:**
- ✅ Checks if Ollama is installed
- ✅ Offers to install via Homebrew
- ✅ Starts Ollama as background service or foreground
- ✅ Lists installed models
- ✅ Offers to pull recommended models:
  - **llama3** (4.7GB) - Fast and general-purpose SQL generation
  - **codellama** (3.8GB) - Code-focused SQL generation
  - **duckdb-nsql** (3.8GB) - DuckDB-specific SQL
  - **nomic-embed-text** (274MB) - Embeddings for semantic caching

**Options:**
- Install Ollama if not present
- Start as background service (auto-starts on boot)
- Start in foreground (manual control)
- Select which models to pull
- Skip embedding model (uses TF-IDF fallback)

---

## Application Startup Scripts

### `../start_all.sh` - Complete Stack Startup

Start everything: Redis, Ollama, backend, and frontend in one command.

```bash
./start_all.sh
```

**What it does:**
1. Checks if Redis is installed and running
2. Starts Redis if not running (daemonized mode)
3. Checks if Ollama is installed and running
4. Starts Ollama if not running (background process)
5. Calls `./start.sh` to start backend + frontend
6. Provides status of all services

**Smart behavior:**
- Only stops services it started (leaves pre-running services active)
- Tracks which services were started by the script
- Shows clear status for each service
- Proper cleanup on Ctrl+C or exit

**Status messages:**
- `"✅ Redis started successfully (will stop on exit)"` - We started it
- `"✅ Redis is already running (will not manage)"` - Pre-existing service

**When to use:**
- First-time development setup
- After system restart
- When you want everything running with one command

---

### `../stop_all.sh` - Complete Stack Shutdown

Stop everything: Redis, Ollama, backend, and frontend.

```bash
./stop_all.sh
```

**What it does:**
1. Stops backend and frontend (calls `./stop.sh`)
2. Stops Ollama (only if started by `start_all.sh`)
3. Stops Redis (only if started by `start_all.sh`)
4. Cleans up PID files and logs

**Smart behavior:**
- Won't stop Redis/Ollama if they were already running before start_all.sh
- Graceful shutdown with proper cleanup
- Clear feedback on what was stopped vs left running

**Example output:**
- `"✅ Redis stopped"` - We started it and stopped it
- `"⏭️  Redis was already running - leaving it active"` - Pre-existing service

---

### `../start.sh` - Application Only Startup

Start just the backend and frontend (assumes Redis/Ollama already running).

```bash
./start.sh
```

**What it does:**
1. Sets up Python virtual environment
2. Installs dependencies if needed
3. Creates sample database if needed
4. Initializes metadata database
5. Checks Ollama connection (warning if not available)
6. Starts backend server on port 8000
7. Starts frontend server on port 3000

**When to use:**
- When Redis/Ollama are already running
- Quick app restart during development
- When you manage Redis/Ollama separately

---

### `../stop.sh` - Application Only Shutdown

Stop just the backend and frontend (leaves Redis/Ollama running).

```bash
./stop.sh
```

**What it does:**
1. Stops backend server
2. Stops frontend server
3. Cleans up log files

---

## Database Scripts

### `create_sample_db.py` - Create Sample Database

Creates a sample SQLite e-commerce database for testing.

```bash
python scripts/create_sample_db.py
```

Creates: `sample_ecommerce.db` with:
- 15 customers
- 4 product categories
- 20 products
- 50 orders
- 123 order items
- 30 reviews

### `create_sample_duckdb.py` - Create Sample DuckDB Database

Creates a sample DuckDB e-commerce database.

```bash
python scripts/create_sample_duckdb.py
```

Creates: `sample_ecommerce.duckdb` with the same schema as SQLite version.

---

## Usage Examples

### Complete Stack (Recommended for Development)

```bash
# First time: Install and setup Redis + Ollama + Models
./scripts/setup_cache.sh

# Daily development: Start everything with one command
./start_all.sh

# When done: Stop everything
./stop_all.sh
```

### Application Only (Redis/Ollama already running)

```bash
# Start just backend + frontend
./start.sh

# Stop just backend + frontend
./stop.sh
```

### First-Time Setup

```bash
# Complete setup (recommended)
./scripts/setup_cache.sh
```

### Redis Only

```bash
# Install and start Redis
./scripts/setup_redis.sh

# Later, if you want to stop Redis
brew services stop redis
```

### Ollama Only

```bash
# Install Ollama and pull models
./scripts/setup_ollama.sh

# Later, pull additional models
ollama pull llama3
```

### Manual Control

```bash
# Start Redis in foreground (this terminal)
redis-server

# Start Ollama in foreground (this terminal)
ollama serve
```

---

## Complete Stack Usage Examples

### Scenario 1: Clean Start (No Services Running)
```bash
# Start everything
./start_all.sh
# Output:
# ✅ Redis started successfully (will stop on exit)
# ✅ Ollama started successfully (will stop on exit)
# ✅ Backend is ready!
# ✅ Frontend is ready!

# Later, stop everything
./stop_all.sh
# Output:
# ✅ Backend server stopped
# ✅ Frontend server stopped
# ✅ Ollama stopped
# ✅ Redis stopped
```

### Scenario 2: Services Already Running
```bash
# Redis and Ollama are already running as services
brew services start redis
brew services start ollama

# Start the application
./start_all.sh
# Output:
# ✅ Redis is already running (will not manage)
# ✅ Ollama is already running (will not manage)
# ✅ Backend is ready!
# ✅ Frontend is ready!

# Stop only the app (leaves Redis/Ollama running)
./stop_all.sh
# Output:
# ✅ Backend server stopped
# ✅ Frontend server stopped
# ⏭️  Ollama was already running - leaving it active
# ⏭️  Redis was already running - leaving it active
```

### Scenario 3: Using Ctrl+C
```bash
./start_all.sh
# Press Ctrl+C
# The cleanup trap runs automatically:
# 🧹 Cleaning up services started by this script...
# 🤖 Stopping Ollama...
# ✅ Ollama stopped
# 💾 Stopping Redis...
# ✅ Redis stopped
# ✨ Cleanup complete
```

---

## Troubleshooting

**Script not executable:**
```bash
chmod +x scripts/*.sh start_all.sh stop_all.sh
```

**start_all.sh not starting Redis:**
- Check if Redis is already running: `redis-cli ping`
- Check the startup messages - look for "(will stop on exit)" vs "(will not manage)"
- If Redis fails to start, check: `redis-server --daemonize yes`
- View the script's service tracking: `cat .services.pid`

**stop_all.sh not stopping services:**
- Only stops services that start_all.sh started
- Check `.services.pid` to see which services are managed
- If services won't stop: `./stop.sh && brew services stop redis && pkill -f "ollama serve"`

**Homebrew not installed:**
```bash
# Install Homebrew first
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Redis connection issues:**
```bash
# Check if Redis is running
redis-cli ping

# Should return: PONG
```

**Ollama connection issues:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Should return JSON with model list
```

---

## See Also

- [Cache Setup Guide](../docs/CACHE_SETUP.md) - Complete cache setup documentation
- [README.md](../README.md) - Main project documentation
- [CHANGELOG.md](../CHANGELOG.md) - Version history and recent changes
