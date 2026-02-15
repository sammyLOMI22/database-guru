# ---- Builder Stage ----
FROM python:3.11-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Production Stage ----
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -u 1000 -s /usr/sbin/nologin appuser

COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser ./src ./src
COPY --chown=appuser:appuser ./alembic ./alembic
COPY --chown=appuser:appuser ./alembic.ini ./alembic.ini
COPY --chown=appuser:appuser ./configs ./configs

# Copy entrypoint
COPY --chown=appuser:appuser ./docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create data directories
RUN mkdir -p /app/data /app/uploads /app/logs && \
    chown -R appuser:appuser /app/data /app/uploads /app/logs

# Remove setuid/setgid binaries to reduce privilege escalation surface
RUN find / -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
