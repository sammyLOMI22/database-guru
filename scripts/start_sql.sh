#!/usr/bin/env bash
# Start SQL sample databases and optionally seed them with data.
#
# Usage:
#   ./scripts/start_sql.sh           # Start Docker DBs + seed all (including SQLite/DuckDB)
#   ./scripts/start_sql.sh --no-seed # Start Docker services only
#   ./scripts/start_sql.sh --db postgresql,sqlite  # Start all, seed specific DBs
#   ./scripts/start_sql.sh --clean   # Drop and recreate before seeding

set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.sql.yml"
SEED_SCRIPT="scripts/seed_sql_data.py"
NO_SEED=false
DB_FILTER=""
CLEAN=""

for arg in "$@"; do
    case "$arg" in
        --no-seed)  NO_SEED=true ;;
        --clean)    CLEAN="--clean" ;;
        --db=*)     DB_FILTER="${arg#--db=}" ;;
        --db)       shift; DB_FILTER="$1" 2>/dev/null || true ;;
    esac
done

echo "Starting SQL services (PostgreSQL + MySQL)..."
docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo "Waiting for services to become healthy..."

wait_for_service() {
    local service="$1"
    local max_wait="$2"
    local elapsed=0
    printf "  %-20s " "$service"
    while [ $elapsed -lt $max_wait ]; do
        status=$(docker compose -f "$COMPOSE_FILE" ps --format json "$service" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null || echo "")
        if [ "$status" = "healthy" ]; then
            echo "ready"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo "timeout (${max_wait}s) - may still be starting"
    return 0
}

wait_for_service "postgresql" 30
wait_for_service "mysql"      60

echo ""

if [ "$NO_SEED" = true ]; then
    echo "Skipping seed (--no-seed)"
else
    echo "Seeding databases..."
    SEED_ARGS=""
    [ -n "$DB_FILTER" ] && SEED_ARGS="--db $DB_FILTER"
    [ -n "$CLEAN" ] && SEED_ARGS="$SEED_ARGS $CLEAN"
    python3 "$SEED_SCRIPT" $SEED_ARGS
fi

echo ""
echo "SQL services are running. Ports:"
echo "  PostgreSQL:  localhost:5433  (user: dbguru / dbguru)"
echo "  MySQL:       localhost:3307  (user: dbguru / dbguru)"
echo "  SQLite:      sample_ecommerce.db    (file-based)"
echo "  DuckDB:      sample_ecommerce.duckdb (file-based)"
echo ""
echo "Stop with: ./scripts/stop_sql.sh"
