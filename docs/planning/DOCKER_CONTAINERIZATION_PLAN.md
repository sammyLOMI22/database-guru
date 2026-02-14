# Dockerize Database Guru - "Run Anywhere" on localhost:3000

**Phase**: 23 - Docker Containerization
**Priority**: HIGH
**Est. Effort**: ~1 week | ~200 lines config (no app code changes)
**Prerequisites**: None (Independent)
**Last Updated**: February 14, 2026

---

## Context

Database Guru currently runs via `start.sh` which requires Python, Node.js, and manual dependency management. The goal is to package the entire app into Docker containers so anyone can `docker compose up` and access it at `localhost:3000` — bringing their own LLM provider, files, and data sources.

## Design Decisions

- **BYO LLM default, optional bundled Ollama**: Default expects users to provide their own LLM endpoint. `--profile ollama` adds a bundled Ollama container with auto model pull and GPU support.
- **Nginx reverse proxy**: Serves built React static files on port 3000, proxies `/api` and `/health` to the backend container.
- **Docker Compose profiles**: Default is lightweight SQLite + BYO LLM. Optional profiles:
  - `--profile ollama` — adds Ollama container with GPU support and auto model pull
  - `--profile full` — adds PostgreSQL + Redis
  - Profiles can be combined: `--profile ollama --profile full`

## Run Modes

| Command | What You Get |
|---------|-------------|
| `docker compose up` | SQLite + BYO LLM (minimal, 2 containers) |
| `docker compose --profile ollama up` | SQLite + bundled Ollama with auto model pull + GPU |
| `docker compose --profile full up` | PostgreSQL + Redis + BYO LLM |
| `docker compose --profile full --profile ollama up` | Everything |

## Architecture

```
User's browser → :3000 → Nginx container
                           ├── static files (React build)
                           └── /api/* → backend:8000 (FastAPI)
                                          ├── SQLite (default) or PostgreSQL (--profile full)
                                          ├── File uploads (volume mount)
                                          └── User's LLM (external via OLLAMA_BASE_URL, or bundled via --profile ollama)
```

---

## Files to Create/Modify

### 1. `frontend/Dockerfile` (NEW)

Multi-stage build:
- **Stage 1 (`build`)**: `node:20-alpine`, `npm ci`, `npm run build` with `VITE_API_URL=""` (empty so Nginx proxy works)
- **Stage 2 (`runtime`)**: `nginx:alpine`, copy `dist/` to `/usr/share/nginx/html`, copy custom nginx config

### 2. `frontend/nginx.conf` (NEW)

```nginx
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing - serve index.html for all non-file routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API and health to backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;  # Long timeout for LLM queries
    }

    location /health {
        proxy_pass http://backend:8000;
    }

    # Cache static assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 3. `Dockerfile` (MODIFY — backend only)

Update existing Dockerfile:
- Copy `alembic/` and `alembic.ini` (currently missing — needed for auto-migrations on startup)
- Copy `configs/` directory
- Copy `scripts/create_sample_db.py` and `init_system_settings.py` for first-run setup
- Create `/app/uploads` and `/app/data` directories owned by appuser
- Add `curl` for healthcheck (replace Python-based healthcheck)
- Copy `.env.docker` as fallback defaults

```dockerfile
FROM python:3.11-slim as builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev libpq-dev && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -u 1000 appuser
COPY --from=builder /home/appuser/.local /home/appuser/.local
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser ./src ./src
COPY --chown=appuser:appuser ./configs ./configs
COPY --chown=appuser:appuser ./alembic ./alembic
COPY --chown=appuser:appuser ./alembic.ini ./alembic.ini
COPY --chown=appuser:appuser ./scripts ./scripts
COPY --chown=appuser:appuser ./init_system_settings.py ./init_system_settings.py
COPY --chown=appuser:appuser ./.env.docker ./.env

# Create data directories
RUN mkdir -p /app/data /app/uploads /app/logs && \
    chown -R appuser:appuser /app/data /app/uploads /app/logs

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4. `docker-compose.yml` (REWRITE)

```yaml
services:
  backend:
    build: .
    container_name: database-guru-backend
    env_file: .env.docker
    volumes:
      - db_data:/app/data          # SQLite DB + DuckDB
      - uploads:/app/uploads       # File uploads persist
      - ./logs:/app/logs           # Logs on host
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      start_period: 10s
      retries: 3
    networks:
      - app-network

  frontend:
    build: ./frontend
    container_name: database-guru-frontend
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - app-network

  # --- Profile: full (docker compose --profile full up) ---
  postgres:
    image: postgres:16-alpine
    profiles: ["full"]
    container_name: database-guru-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-dbguru}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dbguru}
      POSTGRES_DB: ${POSTGRES_DB:-database_guru}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    profiles: ["full"]
    container_name: database-guru-redis
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - app-network

  # --- Profile: ollama (docker compose --profile ollama up) ---
  ollama:
    image: ollama/ollama:latest
    profiles: ["ollama"]
    container_name: database-guru-ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    networks:
      - app-network

  # Init container: pulls default model on first start
  ollama-init:
    image: ollama/ollama:latest
    profiles: ["ollama"]
    container_name: database-guru-ollama-init
    depends_on:
      ollama:
        condition: service_started
    entrypoint: ["/bin/sh", "-c", "sleep 5 && ollama pull ${OLLAMA_MODEL:-llama3.2:latest}"]
    environment:
      OLLAMA_HOST: http://ollama:11434
    networks:
      - app-network

volumes:
  db_data:
  uploads:
  postgres_data:
  redis_data:
  ollama_data:

networks:
  app-network:
    driver: bridge
```

### 5. `.env.docker` (NEW)

Default environment for Docker deployment:

```env
APP_NAME=Database Guru
VERSION=2.0.0
DEBUG=False

# Metadata DB (SQLite default — override with Postgres for --profile full)
DATABASE_URL=sqlite+aiosqlite:////app/data/database_guru.db

# LLM - Point to your own Ollama or compatible API
# For host machine Ollama: http://host.docker.internal:11434
# For remote Ollama: http://your-server:11434
# For --profile ollama (bundled): http://ollama:11434
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest
OLLAMA_ALLOW_MODEL_SELECTION=True

# Redis (disabled by default, enable with --profile full)
REDIS_URL=

# File uploads
FILE_UPLOAD_DIR=/app/uploads
FILE_MAX_SIZE_MB=100
FILE_AUTO_CLEANUP_DAYS=30

# Security
SECRET_KEY=change-me-in-production

# Query settings
MAX_QUERY_ROWS=1000
QUERY_TIMEOUT_SECONDS=30
ALLOW_WRITE_OPERATIONS=False
```

### 6. `.env.docker.full` (NEW)

Override for `--profile full`:

```env
DATABASE_URL=postgresql+asyncpg://dbguru:dbguru@postgres:5432/database_guru
REDIS_URL=redis://redis:6379
```

### 7. `.dockerignore` (NEW)

```
venv/
node_modules/
frontend/node_modules/
frontend/dist/
*.pyc
__pycache__/
.git/
.env
*.db
logs/
uploads/
.pytest_cache/
tests/
docs/
*.md
```

### 8. Minor backend fix: `src/config/settings.py`

Ensure `FILE_UPLOAD_DIR` works with absolute paths in Docker. Currently uses relative `"uploads"` — needs to respect the env var `/app/uploads` without modification.

---

## Implementation Order

1. Create `.dockerignore`
2. Create `.env.docker` and `.env.docker.full`
3. Update `Dockerfile` (backend) — add alembic, curl, data dirs
4. Create `frontend/nginx.conf`
5. Create `frontend/Dockerfile`
6. Rewrite `docker-compose.yml` with profiles
7. Verify `settings.py` handles absolute `FILE_UPLOAD_DIR` and `DATABASE_URL` paths correctly
8. Test build and startup

---

## Verification

1. **Build**: `docker compose build` — both images build successfully
2. **Default (SQLite + BYO LLM)**: `docker compose up` — app at `localhost:3000`, API proxied via Nginx
3. **Bundled Ollama**: `docker compose --profile ollama up` — Ollama starts, model auto-pulled, `OLLAMA_BASE_URL=http://ollama:11434`
4. **Full stack**: `docker compose --profile full --profile ollama up` — all services start
5. **BYO LLM**: Default `.env.docker` points to `host.docker.internal:11434`, verify LLM calls reach host
6. **File uploads**: Upload CSV, verify persistence across container restarts (volume mount)
7. **Data persistence**: Create connection, restart containers, verify it persists (SQLite in volume)
8. **Nginx proxy**: `/api/*` routes proxy correctly, SPA deep links work
