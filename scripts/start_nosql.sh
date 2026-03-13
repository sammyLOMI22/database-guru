#!/usr/bin/env bash
# Start NoSQL sample databases and optionally seed them with data.
#
# Usage:
#   ./scripts/start_nosql.sh           # Start all + seed
#   ./scripts/start_nosql.sh --no-seed # Start only, skip seeding
#   ./scripts/start_nosql.sh --db mongodb,redis  # Start all, seed specific DBs

set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE_FILE="docker-compose.nosql.yml"
SEED_SCRIPT="scripts/seed_nosql_data.py"
NO_SEED=false
DB_FILTER=""
CLEAN=""

while [ $# -gt 0 ]; do
    case "$1" in
        --no-seed)  NO_SEED=true ;;
        --clean)    CLEAN="--clean" ;;
        --db=*)     DB_FILTER="${1#--db=}" ;;
        --db)       shift; DB_FILTER="${1:?--db requires a value}" ;;
    esac
    shift
done

echo "Starting NoSQL services..."
docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo "Waiting for services to become healthy..."

# Wait function with timeout
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

wait_for_service "mongodb"       30
wait_for_service "redis"         15
wait_for_service "cassandra"     120
wait_for_service "dynamodb"      15
wait_for_service "elasticsearch" 60

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
echo "NoSQL services are running. Ports:"
echo "  MongoDB:       localhost:27017"
echo "  Redis:         localhost:6380"
echo "  Cassandra:     localhost:9042"
echo "  DynamoDB:      localhost:8001"
echo "  Elasticsearch: localhost:9200"
echo ""
echo "Stop with: ./scripts/stop_nosql.sh"
