#!/bin/bash
# setup_test_databases.sh - One-command setup for all test databases
#
# Sets up Docker-based and file-based test databases for connection pooling tests:
# - PostgreSQL (Docker, port 5433)
# - MySQL (Docker, port 3307)
# - MongoDB (Docker, port 27018) - for future use
# - SQLite (file-based)
# - DuckDB (file-based)
#
# Usage:
#   ./scripts/setup_test_databases.sh [--skip-docker]
#
# Options:
#   --skip-docker    Skip Docker container setup (only initialize file-based DBs)

set -e

SKIP_DOCKER=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-docker]"
            exit 1
            ;;
    esac
done

echo "🚀 Setting up test databases for connection pooling tests..."
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python package
python_package_exists() {
    python -c "import $1" 2>/dev/null
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! $SKIP_DOCKER; then
    if ! command_exists docker; then
        echo "❌ ERROR: Docker is not installed"
        echo "   Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        echo "❌ ERROR: Docker Compose is not installed"
        echo "   Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    echo "✅ Docker and Docker Compose are installed"
fi

if ! command_exists python; then
    echo "❌ ERROR: Python is not installed"
    exit 1
fi
echo "✅ Python is installed"

# Check for netcat (for port checking)
if ! command_exists nc; then
    echo "⚠️  WARNING: netcat (nc) is not installed. Port checking will be skipped."
    echo "   Install with: brew install netcat (macOS) or apt-get install netcat (Linux)"
fi

echo ""

# Docker-based databases
if ! $SKIP_DOCKER; then
    echo "🐳 Starting Docker containers..."

    # Check which docker-compose command to use
    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi

    # Start containers
    cd "$(dirname "$0")/.."  # Go to project root
    $DOCKER_COMPOSE -f tests/fixtures/docker-compose.test.yml up -d

    echo ""
    echo "⏳ Waiting for databases to be ready..."
    echo ""

    # Wait for PostgreSQL
    if command_exists nc; then
        ./scripts/wait_for_db.sh postgres-test 5433 || echo "⚠️  PostgreSQL health check failed, continuing anyway..."
    else
        echo "⏳ Waiting 10 seconds for PostgreSQL..."
        sleep 10
    fi

    # Wait for MySQL
    if command_exists nc; then
        ./scripts/wait_for_db.sh mysql-test 3307 || echo "⚠️  MySQL health check failed, continuing anyway..."
    else
        echo "⏳ Waiting 10 seconds for MySQL..."
        sleep 10
    fi

    echo ""
fi

# Initialize databases
echo "🔧 Initializing databases with sample data..."
echo ""

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
elif [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# PostgreSQL
if ! $SKIP_DOCKER; then
    echo "📊 PostgreSQL..."
    if python scripts/init_postgres_test.py; then
        echo ""
    else
        echo "⚠️  WARNING: PostgreSQL initialization failed"
        echo ""
    fi
fi

# MySQL
if ! $SKIP_DOCKER; then
    echo "📊 MySQL..."
    if python scripts/init_mysql_test.py; then
        echo ""
    else
        echo "⚠️  WARNING: MySQL initialization failed"
        echo ""
    fi
fi

# SQLite
echo "📊 SQLite..."
if python scripts/init_sqlite_test.py; then
    echo ""
else
    echo "⚠️  WARNING: SQLite initialization failed"
    echo ""
fi

# DuckDB
echo "📊 DuckDB..."
if python scripts/init_duckdb_test.py; then
    echo ""
else
    echo "⚠️  WARNING: DuckDB initialization failed"
    echo ""
fi

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Test database setup complete!"
echo ""
if ! $SKIP_DOCKER; then
    echo "Docker Databases:"
    echo "  🐘 PostgreSQL: localhost:5433"
    echo "     - Database: test_pooling"
    echo "     - User: test_user / test_pass"
    echo "     - Connection: postgresql://test_user:test_pass@localhost:5433/test_pooling"
    echo ""
    echo "  🐬 MySQL: localhost:3307"
    echo "     - Database: test_pooling"
    echo "     - User: test_user / test_pass"
    echo "     - Connection: mysql://test_user:test_pass@localhost:3307/test_pooling"
    echo ""
    echo "  🍃 MongoDB: localhost:27018 (for future use)"
    echo "     - Database: test_pooling"
    echo "     - Connection: mongodb://localhost:27018/test_pooling"
    echo ""
fi
echo "File-based Databases:"
echo "  📁 SQLite: tests/fixtures/test_pooling.db"
echo "     - Connection: sqlite+aiosqlite:///tests/fixtures/test_pooling.db"
echo ""
echo "  🦆 DuckDB: tests/fixtures/test_pooling.duckdb"
echo "     - Connection: duckdb:///tests/fixtures/test_pooling.duckdb"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Next steps:"
echo "   1. Run pooling tests:"
echo "      pytest tests/test_connection_pool_manager.py -v"
echo "      pytest tests/test_pooled_query_execution.py -v"
echo ""
echo "   2. Stop Docker containers when done:"
if docker compose version >/dev/null 2>&1; then
    echo "      docker compose -f tests/fixtures/docker-compose.test.yml down"
else
    echo "      docker-compose -f tests/fixtures/docker-compose.test.yml down"
fi
echo ""
echo "   3. Remove test data:"
echo "      rm tests/fixtures/*.db tests/fixtures/*.duckdb"
if ! $SKIP_DOCKER; then
    if docker compose version >/dev/null 2>&1; then
        echo "      docker compose -f tests/fixtures/docker-compose.test.yml down -v"
    else
        echo "      docker-compose -f tests/fixtures/docker-compose.test.yml down -v"
    fi
fi
echo ""
