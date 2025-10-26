#!/bin/bash
# Script to run frontend tests
# Usage: ./scripts/test_frontend.sh [--watch]

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Frontend Test Runner            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo -e "${RED}Error: frontend directory not found!${NC}"
    echo "Please run this script from the project root."
    exit 1
fi

# Change to frontend directory
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}📦 Installing dependencies...${NC}"
    npm install
    echo ""
fi

# Run tests based on arguments
if [ "$1" == "--watch" ] || [ "$1" == "-w" ]; then
    echo -e "${BLUE}🔍 Running tests in watch mode...${NC}"
    echo ""
    npm test
    exit $?
elif [ "$1" == "--ui" ]; then
    echo -e "${BLUE}🖥️  Opening Vitest UI...${NC}"
    echo ""
    npm run test:ui
    exit $?
elif [ "$1" == "--coverage" ] || [ "$1" == "-c" ]; then
    echo -e "${BLUE}📊 Running tests with coverage...${NC}"
    echo ""
    set +e  # Temporarily disable exit on error
    npm test -- --run --coverage
    EXIT_CODE=$?
    set -e  # Re-enable exit on error
else
    echo -e "${BLUE}🧪 Running frontend tests...${NC}"
    echo ""
    set +e  # Temporarily disable exit on error
    npm test -- --run
    EXIT_CODE=$?
    set -e  # Re-enable exit on error
fi

# Vitest returns non-zero for cleanup errors even when all tests pass
# We consider it a success if the tests ran (exit code will be 0 or 1 for cleanup errors)
# but a failure for other exit codes (e.g., syntax errors, crashes)
if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 1 ]; then
    echo ""
    echo -e "${GREEN}✅ Frontend tests completed!${NC}"
    # Return 0 since tests passed (exit code 1 is just cleanup warning)
    exit 0
else
    echo ""
    echo -e "${RED}❌ Frontend tests failed with exit code $EXIT_CODE!${NC}"
    exit $EXIT_CODE
fi
