#!/usr/bin/env bash
# Stop NoSQL sample databases.
#
# Usage:
#   ./scripts/stop_nosql.sh       # Stop containers (keep data)
#   ./scripts/stop_nosql.sh -v    # Stop + remove volumes (delete all data)

set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.nosql.yml"

if [[ "${1:-}" == "-v" ]]; then
    echo "Stopping NoSQL services and removing volumes..."
    docker compose -f "$COMPOSE_FILE" down -v
else
    echo "Stopping NoSQL services (data preserved)..."
    docker compose -f "$COMPOSE_FILE" down
fi

echo "Done."
