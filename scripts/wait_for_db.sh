#!/bin/bash
# wait_for_db.sh - Wait for database to be ready
#
# Usage: ./scripts/wait_for_db.sh <service-name> <port> [max-wait-seconds]
#
# Examples:
#   ./scripts/wait_for_db.sh postgres-test 5433
#   ./scripts/wait_for_db.sh mysql-test 3307
#   ./scripts/wait_for_db.sh mongodb-test 27018

set -e

SERVICE_NAME=${1:-"postgres-test"}
PORT=${2:-5432}
MAX_WAIT=${3:-60}

echo "⏳ Waiting for $SERVICE_NAME to be ready on port $PORT..."

# Function to check if port is open
check_port() {
    nc -z localhost "$PORT" >/dev/null 2>&1
}

# Wait for port to be open
ELAPSED=0
INTERVAL=2

while ! check_port; do
    if [ $ELAPSED -ge $MAX_WAIT ]; then
        echo "❌ ERROR: $SERVICE_NAME did not become ready within ${MAX_WAIT}s"
        exit 1
    fi

    echo "⏳ Waiting for $SERVICE_NAME (${ELAPSED}s / ${MAX_WAIT}s)..."
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

# Additional service-specific health checks
case $SERVICE_NAME in
    postgres-test)
        echo "🔍 Checking PostgreSQL health..."
        for i in {1..10}; do
            if PGPASSWORD=test_pass psql -h localhost -p "$PORT" -U test_user -d test_pooling -c "SELECT 1" >/dev/null 2>&1; then
                echo "✅ PostgreSQL is ready!"
                exit 0
            fi
            echo "⏳ PostgreSQL not ready yet, retrying ($i/10)..."
            sleep 2
        done
        echo "⚠️  PostgreSQL port is open but database queries are not working"
        ;;

    mysql-test)
        echo "🔍 Checking MySQL health..."
        for i in {1..10}; do
            if mysql -h 127.0.0.1 -P "$PORT" -u test_user -ptest_pass -e "SELECT 1" >/dev/null 2>&1; then
                echo "✅ MySQL is ready!"
                exit 0
            fi
            echo "⏳ MySQL not ready yet, retrying ($i/10)..."
            sleep 2
        done
        echo "⚠️  MySQL port is open but database queries are not working"
        ;;

    mongodb-test)
        echo "🔍 Checking MongoDB health..."
        for i in {1..10}; do
            if mongosh --host localhost --port "$PORT" --eval "db.adminCommand('ping')" >/dev/null 2>&1; then
                echo "✅ MongoDB is ready!"
                exit 0
            fi
            echo "⏳ MongoDB not ready yet, retrying ($i/10)..."
            sleep 2
        done
        echo "⚠️  MongoDB port is open but database queries are not working"
        ;;

    *)
        echo "✅ Port $PORT is open (service: $SERVICE_NAME)"
        ;;
esac

exit 0
