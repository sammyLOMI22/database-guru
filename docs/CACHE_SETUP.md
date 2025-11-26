# Cache Setup Guide

This guide explains how to set up Redis and Ollama for Database Guru's caching system.

## 🚀 Quick Start (Automated Setup)

For the fastest setup, use our automated scripts:

```bash
# Complete setup (Redis + Ollama + Models)
./scripts/setup_cache.sh

# Or run individually:
./scripts/setup_redis.sh    # Setup Redis only
./scripts/setup_ollama.sh   # Setup Ollama + Models only
```

The scripts will:
- ✅ Check if Redis/Ollama are installed
- ✅ Offer to install via Homebrew if missing
- ✅ Start services (as background service or foreground)
- ✅ Pull recommended models for Ollama
- ✅ Provide configuration instructions

---

## Overview

Database Guru uses two caching layers:

| Cache Type | Purpose | Backend | Fallback |
|------------|---------|---------|----------|
| **Exact Cache** | Hash-based query caching | Redis | None (disabled) |
| **Semantic Cache** | Similarity-based query matching | Redis + Embeddings | In-memory + TF-IDF |
| **LLM Cache** | Cache SQL generation responses | Redis | In-memory |

## Quick Start

```bash
# Start Redis (required for persistent caching)
brew services start redis

# Verify Ollama is running (for SQL generation)
ollama serve
```

---

## Redis Setup

Redis is used for persistent caching. Without Redis, caches use in-memory storage (data lost on restart).

### Option 1: Homebrew (macOS)

```bash
# Install
brew install redis

# Start as service (auto-starts on boot)
brew services start redis

# Or start manually (foreground)
redis-server

# Stop service
brew services stop redis
```

### Option 2: Docker

```bash
# Run Redis container
docker run -d \
  --name database-guru-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:alpine redis-server --appendonly yes

# With password protection
docker run -d \
  --name database-guru-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:alpine redis-server --appendonly yes --requirepass your-password

# Stop container
docker stop database-guru-redis

# Start existing container
docker start database-guru-redis

# View logs
docker logs database-guru-redis
```

### Option 3: Docker Compose

Add to your `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:alpine
    container_name: database-guru-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  redis-data:
```

Then run:
```bash
docker-compose up -d redis
```

### Verify Redis

```bash
# Test connection
redis-cli ping
# Expected: PONG

# Check info
redis-cli info server | head -5
```

### Configure Redis URL

Set in `.env` file:

```bash
# Local Redis
REDIS_URL=redis://localhost:6379

# Docker Redis (from host)
REDIS_URL=redis://localhost:6379

# Redis with password
REDIS_URL=redis://:your-password@localhost:6379

# Remote Redis
REDIS_URL=redis://user:password@redis-host:6379
```

---

## Ollama Setup

Ollama is used for:
1. **SQL Generation** - Converting natural language to SQL
2. **Embeddings** (optional) - For semantic similarity matching

### Option 1: Local Installation (macOS)

```bash
# Install
brew install ollama

# Start server (keeps running in background)
brew services start ollama

# Or start manually
ollama serve

# Pull models
ollama pull llama3              # For SQL generation
ollama pull nomic-embed-text    # For embeddings (optional, improves semantic cache)
```

### Option 2: Docker

```bash
# Run Ollama container (CPU only)
docker run -d \
  --name database-guru-ollama \
  -p 11434:11434 \
  -v ollama-data:/root/.ollama \
  ollama/ollama

# Run with GPU support (NVIDIA)
docker run -d \
  --name database-guru-ollama \
  --gpus all \
  -p 11434:11434 \
  -v ollama-data:/root/.ollama \
  ollama/ollama

# Pull models into container
docker exec database-guru-ollama ollama pull llama3
docker exec database-guru-ollama ollama pull nomic-embed-text

# View logs
docker logs database-guru-ollama
```

### Option 3: Docker Compose

Add to your `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama
    container_name: database-guru-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped
    # Uncomment for GPU support:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]

volumes:
  ollama-data:
```

Then run:
```bash
docker-compose up -d ollama

# Pull models
docker exec database-guru-ollama ollama pull llama3
```

### Verify Ollama

```bash
# Check if running
curl http://localhost:11434/api/tags

# List models
ollama list

# Test generation
curl http://localhost:11434/api/generate -d '{
  "model": "llama3",
  "prompt": "Hello",
  "stream": false
}'
```

### Configure Ollama URL

Set in `.env` file:

```bash
# Local Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Docker Ollama (from host)
OLLAMA_BASE_URL=http://localhost:11434

# Remote Ollama
OLLAMA_BASE_URL=http://ollama-host:11434

# Default model for SQL generation
OLLAMA_MODEL=llama3
```

---

## Recommended Models

| Model | Size | Purpose | Pull Command |
|-------|------|---------|--------------|
| `llama3` | 4.7GB | General SQL generation | `ollama pull llama3` |
| `qwen2.5-coder:32b` | 19GB | Best for complex SQL | `ollama pull qwen2.5-coder:32b` |
| `codellama` | 3.8GB | Code-focused | `ollama pull codellama` |
| `nomic-embed-text` | 274MB | Embeddings for semantic cache | `ollama pull nomic-embed-text` |
| `duckdb-nsql` | 3.8GB | DuckDB-specific SQL | `ollama pull duckdb-nsql` |

---

## Full Docker Compose Setup

Complete `docker-compose.yml` for all services:

```yaml
version: '3.8'

services:
  # Redis for caching
  redis:
    image: redis:alpine
    container_name: database-guru-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Ollama for LLM
  ollama:
    image: ollama/ollama
    container_name: database-guru-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis-data:
  ollama-data:
```

Start all services:
```bash
docker-compose up -d

# Pull required models
docker exec database-guru-ollama ollama pull llama3
docker exec database-guru-ollama ollama pull nomic-embed-text

# Check status
docker-compose ps
```

---

## Troubleshooting

### Redis Issues

**Connection refused:**
```bash
# Check if Redis is running
redis-cli ping

# Check port
lsof -i :6379

# Restart Redis
brew services restart redis
# or
docker restart database-guru-redis
```

**Memory issues:**
```bash
# Check Redis memory usage
redis-cli info memory

# Clear all caches
redis-cli FLUSHALL
```

### Ollama Issues

**Connection refused:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check port
lsof -i :11434

# Restart Ollama
brew services restart ollama
# or
docker restart database-guru-ollama
```

**Model not found:**
```bash
# List available models
ollama list

# Pull missing model
ollama pull llama3
```

**Slow responses:**
- Consider using a smaller model (`llama3` instead of `qwen2.5-coder:32b`)
- Enable GPU acceleration if available
- Check system resources: `htop` or `docker stats`

### Cache Not Working

**Check backend logs:**
```bash
# Look for cache-related messages
tail -f backend.log | grep -i cache
```

**Common log messages:**
- `Redis not connected, using memory fallback` - Redis not running
- `Using TF-IDF fallback for embeddings` - Ollama embeddings not available
- `Semantic cache hit` - Cache is working!

---

## Environment Variables Reference

```bash
# .env file

# Redis
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600  # Cache expiration in seconds

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_ALLOW_MODEL_SELECTION=true
```

---

## Performance Tips

1. **Use Redis** - In-memory fallback is slower and doesn't persist
2. **Pull embedding model** - `nomic-embed-text` gives better semantic matching than TF-IDF
3. **Use SSD storage** - For Redis persistence and Ollama models
4. **Monitor cache hit rates** - Check the Cache dashboard in the UI
5. **Adjust TTL** - Lower TTL for frequently changing data, higher for stable schemas
