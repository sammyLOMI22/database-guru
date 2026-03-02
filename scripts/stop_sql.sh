#!/usr/bin/env bash
# Stop SQL sample databases (PostgreSQL + MySQL).
#
# Usage:
#   ./scripts/stop_sql.sh       # Stop containers (keep data)
#   ./scripts/stop_sql.sh -v    # Stop + remove volumes (delete all data)

set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.sql.yml"

if [[ "${1:-}" == "-v" ]]; then
    echo "Stopping SQL services and removing volumes..."
    docker compose -f "$COMPOSE_FILE" down -v
else
    echo "Stopping SQL services (data preserved)..."
    docker compose -f "$COMPOSE_FILE" down
fi

echo "Done."
echo ""
echo "Note: SQLite (sample_ecommerce.db) and DuckDB (sample_ecommerce.duckdb) are file-based."
echo "Delete them manually if needed."
