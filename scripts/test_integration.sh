#!/bin/bash
# Script to run integration tests (requires server)
# Usage: ./scripts/test_integration.sh [--no-server]

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Integration Test Runner         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: venv directory not found!${NC}"
    echo "Please create a virtual environment first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if --no-server flag is provided
START_SERVER=true
if [ "$1" == "--no-server" ]; then
    START_SERVER=false
    echo -e "${YELLOW}⚠️  Assuming server is already running...${NC}"
    echo ""
fi

SERVER_PID=""

# Function to cleanup on exit
cleanup() {
    if [ ! -z "$SERVER_PID" ]; then
        echo ""
        echo -e "${BLUE}🛑 Stopping test server (PID: $SERVER_PID)...${NC}"
        kill $SERVER_PID 2>/dev/null || true
        sleep 1
        # Force kill if still running
        kill -9 $SERVER_PID 2>/dev/null || true
    fi
}

# Register cleanup function
trap cleanup EXIT INT TERM

if [ "$START_SERVER" = true ]; then
    echo -e "${BLUE}🚀 Starting test server...${NC}"

    # Start server in background
    uvicorn src.main:app --host 0.0.0.0 --port 8000 > server_test.log 2>&1 &
    SERVER_PID=$!

    echo -e "${BLUE}   Server PID: $SERVER_PID${NC}"

    # Wait for server to be ready
    echo -e "${BLUE}⏳ Waiting for server to be ready...${NC}"
    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Server is ready!${NC}"
            echo ""
            break
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))

        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo -e "${RED}❌ Server failed to start within 30 seconds${NC}"
            echo ""
            echo "Server logs:"
            tail -20 server_test.log
            exit 1
        fi

        sleep 1
    done
fi

# Run integration tests
echo -e "${BLUE}🧪 Running integration tests...${NC}"
echo ""

eval "python -m pytest -m 'integration' -v --tb=short"

# Check exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All integration tests passed!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some integration tests failed!${NC}"
    if [ "$START_SERVER" = true ]; then
        echo ""
        echo "Server logs (last 30 lines):"
        tail -30 server_test.log
    fi
    exit 1
fi
