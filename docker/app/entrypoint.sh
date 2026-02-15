#!/bin/bash
set -e

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
url = settings.DATABASE_URL.replace('+aiosqlite', '').replace('+asyncpg', '')
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
