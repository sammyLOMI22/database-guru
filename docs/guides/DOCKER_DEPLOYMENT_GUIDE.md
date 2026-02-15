# Docker Deployment Guide

Deploy Database Guru with a single command using Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24.0+
- [Docker Compose](https://docs.docker.com/compose/install/) v2.20+ (included with Docker Desktop)
- 4GB+ RAM available for containers
- (Optional) [Ollama](https://ollama.com) installed on host for BYO LLM mode
- (Optional) NVIDIA GPU + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) for GPU-accelerated Ollama

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-org/database-guru.git
cd database-guru

# 2. Copy and edit environment variables
cp .env.docker.example .env

# 3. Start the app
docker compose up -d

# 4. Open in browser
open http://localhost:3000
```

The app starts with SQLite (zero-config) and connects to Ollama on your host machine.

## Run Modes

### Default: SQLite + BYO LLM

```bash
docker compose up -d
```

- **Database**: SQLite (persisted in Docker volume)
- **LLM**: Connects to Ollama on your host machine at `http://host.docker.internal:11434`
- **Services**: backend + frontend (nginx)

Make sure Ollama is running on your host: `ollama serve`

### Bundled Ollama

```bash
docker compose --profile ollama up -d
```

Adds a containerized Ollama instance. The configured model is automatically pulled on first start.

To use GPU acceleration (NVIDIA only):
```bash
docker compose --profile ollama -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Update `OLLAMA_BASE_URL` in your `.env`:
```env
OLLAMA_BASE_URL=http://ollama:11434
```

### Full Stack: PostgreSQL + Redis

```bash
docker compose --profile full up -d
```

Adds PostgreSQL 16 and Redis 7. Update your `.env`:
```env
DATABASE_URL=postgresql+asyncpg://dbguru:dbguru_pass@postgres:5432/database_guru
REDIS_URL=redis://redis:6379
```

### Everything

```bash
docker compose --profile full --profile ollama up -d
```

Update `.env` with both Ollama and PostgreSQL/Redis overrides.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2:latest` | Model to use / auto-pull |
| `SECRET_KEY` | `change-me-in-production` | App secret key |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/database_guru.db` | Database connection string |
| `REDIS_URL` | *(empty = disabled)* | Redis URL for caching |
| `POSTGRES_USER` | `dbguru` | PostgreSQL username (full profile) |
| `POSTGRES_PASSWORD` | `dbguru_pass` | PostgreSQL password (full profile) |
| `POSTGRES_DB` | `database_guru` | PostgreSQL database name (full profile) |

## Volume Management

| Volume | Purpose | Backup Command |
|--------|---------|---------------|
| `dbguru-data` | SQLite database | `docker run --rm -v dbguru-data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz -C /data .` |
| `dbguru-uploads` | Uploaded CSV/Excel files | Same pattern with `dbguru-uploads` |
| `dbguru-logs` | Application logs | Same pattern with `dbguru-logs` |
| `ollama-models` | Ollama model weights | Typically re-pulled, not backed up |
| `postgres-data` | PostgreSQL data | Use `pg_dump` inside container |
| `redis-data` | Redis persistence | Typically ephemeral |

### Reset all data

```bash
docker compose down -v
```

## Common Commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild after code changes
docker compose build
docker compose up -d

# Check health
docker compose ps
curl http://localhost:3000/health

# Shell into backend
docker compose exec backend bash

# Run Alembic migration manually
docker compose exec backend alembic upgrade head

# Stop everything
docker compose down
```

## Troubleshooting

### Frontend shows 502 Bad Gateway
The backend hasn't started yet. Check `docker compose logs backend` and wait for health check to pass.

### Ollama connection refused (BYO mode)
- Ensure Ollama is running on your host: `ollama serve`
- On Linux, verify `host.docker.internal` resolves: `docker compose exec backend ping host.docker.internal`

### Model not found (ollama profile)
Check the `ollama-pull` service logs: `docker compose logs ollama-pull`

### Database migration errors
Check backend logs: `docker compose logs backend`. Alembic runs automatically on startup.

### File uploads fail with 413
The nginx config allows 100MB uploads. For larger files, edit `docker/nginx/nginx.conf` and increase `client_max_body_size`.

### Slow LLM responses timeout
Nginx is configured with 120s proxy timeout. For very slow models, edit `proxy_read_timeout` in `docker/nginx/nginx.conf`.

## Production Tips

1. **Change `SECRET_KEY`** to a strong random value
2. **Use the `full` profile** with PostgreSQL for concurrent users
3. **Set up TLS** with a reverse proxy (Traefik, Caddy) in front of port 3000
4. **Monitor health** via `GET /health` endpoint
5. **Back up volumes** regularly (see Volume Management section)
6. **Pin image tags** in docker-compose.yml for reproducible deployments
