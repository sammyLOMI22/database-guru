#!/bin/bash
set -e

# Ensure data directories exist (volumes may mount over them)
mkdir -p /app/data /app/uploads /app/logs

echo "Starting Database Guru backend..."
exec "$@"
