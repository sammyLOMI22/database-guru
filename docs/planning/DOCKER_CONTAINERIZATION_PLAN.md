# Dockerize Database Guru - "Run Anywhere" on localhost:3000

**Phase**: 23 - Docker Containerization
**Priority**: HIGH
**Status**: Implemented
**Last Updated**: February 14, 2026

---

## Context

Database Guru currently runs via `start.sh` which requires Python, Node.js, and manual dependency management. The goal is to package the entire app into Docker containers so anyone can `docker compose up` and access it at `localhost:3000` — bringing their own LLM provider, files, and data sources.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Docker Network (dbguru)             │
│                                                      │
│  ┌──────────┐    ┌──────────┐                        │
│  │ frontend │───▶│ backend  │    Always-on            │
│  │ (nginx)  │    │ (uvicorn)│                        │
│  │ :3000    │    │ :8000    │                        │
│  └──────────┘    └──────────┘                        │
│       │               │                              │
│       │          ┌────┴────┐                         │
│       │          │ Volumes │                         │
│       │          │ data/   │                         │
│       │          │ uploads/│                         │
│       │          │ logs/   │                         │
│       │          └─────────┘                         │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ ollama   │  │ postgres │  │  redis   │  Profiles  │
│  │ :11434   │  │ :5432    │  │  :6379   │           │
│  └──────────┘  └──────────┘  └──────────┘           │
│  profile:       profile:      profile:               │
│  ollama         full          full                    │
└──────────────────────────────────────────────────────┘
```

## Run Modes

| Command | What You Get |
|---------|-------------|
| `docker compose up` | SQLite + BYO LLM (minimal, 2 containers) |
| `docker compose --profile ollama up` | + bundled Ollama with auto model pull |
| `docker compose --profile full up` | + PostgreSQL + Redis |
| `docker compose --profile full --profile ollama up` | Everything |

For GPU acceleration: `docker compose --profile ollama -f docker-compose.yml -f docker-compose.gpu.yml up`

## Design Decisions

1. **Nginx serves frontend + proxies API** — single entry point on :3000, no CORS needed
2. **Nginx config mounted via volume** — not baked into image, easy to customize
3. **`host.docker.internal` for default Ollama** — zero-config on Mac/Windows, `extra_hosts` for Linux
4. **GPU config in separate `docker-compose.gpu.yml`** — base ollama works CPU-only on any system
5. **Single uvicorn worker by default** — SQLite write-lock safety; full profile users can increase
6. **Alembic runs in app lifespan** — no separate init container or entrypoint migration step
7. **`pip install --prefix=/install`** — cleaner multi-stage copy than `--user`
8. **curl for health checks** — reliable, no Python dependency required

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Backend multi-stage build (Python 3.11-slim) |
| `frontend/Dockerfile` | Frontend build (Node 20) + nginx (1.25-alpine) |
| `docker-compose.yml` | Service orchestration with profiles |
| `docker-compose.gpu.yml` | NVIDIA GPU override for Ollama |
| `docker/nginx/nginx.conf` | Reverse proxy + SPA routing + asset caching |
| `docker/app/entrypoint.sh` | Backend directory creation before start |
| `.dockerignore` | Build context exclusions |
| `.env.docker.example` | Environment variable template |
| `docs/guides/DOCKER_DEPLOYMENT_GUIDE.md` | User-facing deployment guide |

## Volumes

| Volume | Container Path | Purpose |
|--------|---------------|---------|
| `dbguru-data` | `/app/data/` | SQLite database |
| `dbguru-uploads` | `/app/uploads/` | User CSV/Excel files |
| `dbguru-logs` | `/app/logs/` | Application logs |
| `ollama-models` | `/root/.ollama` | Ollama model weights |
| `postgres-data` | `/var/lib/postgresql/data` | PostgreSQL data |
| `redis-data` | `/data` | Redis persistence |

## Verification

```bash
# Build
docker compose build

# Default mode
docker compose up -d
curl http://localhost:3000        # React app
curl http://localhost:3000/health # Backend health via proxy

# Ollama profile
docker compose --profile ollama up -d
docker compose logs ollama-pull   # Model pulled

# Full profile (set DATABASE_URL + REDIS_URL in .env)
docker compose --profile full up -d

# Data persistence
docker compose down && docker compose up -d  # Data survives restart
```
