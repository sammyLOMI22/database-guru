#!/bin/bash
set -e

# Validate required configuration
if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY is not set. Generate one with: openssl rand -hex 32" >&2
    exit 1
fi

# Ensure data directories exist (volumes may mount over them)
mkdir -p /app/data /app/uploads /app/logs

# Run database migrations
echo "Running database migrations..."

# Check if alembic has ever been run (i.e., alembic_version table exists)
CURRENT=$(python -m alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' | head -1)

if [ -z "$CURRENT" ]; then
    # Fresh database — create all tables from models, then stamp as current
    echo "Fresh database detected. Creating schema from models..."
    python -c "
from src.config.settings import Settings
from src.database.connection import Base
from src.database import models  # register models
from sqlalchemy import create_engine

settings = Settings()
url = settings.DATABASE_URL
if '+aiosqlite' in url:
    url = url.replace('+aiosqlite', '')
elif '+asyncpg' in url:
    url = url.replace('+asyncpg', '+psycopg2')
engine = create_engine(url)
Base.metadata.create_all(engine)
engine.dispose()
print('Schema created successfully.')
"
    python -m alembic stamp head
    echo "Database stamped at latest migration."
else
    echo "Existing database detected. Running migrations..."
    python -m alembic upgrade head
fi

echo "Starting Database Guru backend..."
export MIGRATIONS_HANDLED=1
exec "$@"
