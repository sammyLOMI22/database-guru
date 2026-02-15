#!/bin/bash
set -e

# Ensure data directories exist (volumes may mount over them)
mkdir -p /app/data /app/uploads /app/logs

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head

echo "Starting Database Guru backend..."
exec "$@"
