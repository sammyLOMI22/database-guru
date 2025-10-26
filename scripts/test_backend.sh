#!/bin/bash
# Script to run backend unit tests (no server required)
# Usage: ./scripts/test_backend.sh [--coverage] [--verbose]

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Backend Unit Test Runner        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: venv directory not found!${NC}"
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Parse arguments
VERBOSE=false
COVERAGE=false

for arg in "$@"; do
    case $arg in
        --coverage|-c)
            COVERAGE=true
            ;;
        --verbose|-v)
            VERBOSE=true
            ;;
        --help|-h)
            echo "Usage: ./scripts/test_backend.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --coverage, -c    Run tests with coverage report"
            echo "  --verbose, -v     Run tests in verbose mode"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./scripts/test_backend.sh                    # Run unit tests"
            echo "  ./scripts/test_backend.sh --coverage         # Run with coverage"
            echo "  ./scripts/test_backend.sh --verbose          # Run with verbose output"
            echo "  ./scripts/test_backend.sh -c -v              # Both coverage and verbose"
            exit 0
            ;;
    esac
done

# Build pytest command with all options
PYTEST_OPTS="-m 'not integration'"

if [ "$COVERAGE" = true ]; then
    PYTEST_OPTS="$PYTEST_OPTS --cov=src --cov-report=term-missing --cov-report=html"
    echo -e "${BLUE}📊 Running with coverage analysis...${NC}"
fi

if [ "$VERBOSE" = true ]; then
    PYTEST_OPTS="$PYTEST_OPTS -v"
    echo -e "${BLUE}🔍 Running in verbose mode...${NC}"
else
    PYTEST_OPTS="$PYTEST_OPTS -q"
fi

echo -e "${BLUE}🧪 Running backend unit tests (no server required)...${NC}"
echo -e "${YELLOW}Note: Integration tests are excluded. Use test_integration.sh to run those.${NC}"
echo ""

# Run tests
eval "python -m pytest $PYTEST_OPTS"

# Check exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All backend unit tests passed!${NC}"

    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}📊 Coverage report generated:${NC}"
        echo "  - Terminal: See above"
        echo "  - HTML: open htmlcov/index.html"
    fi
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some backend tests failed!${NC}"
    exit 1
fi
