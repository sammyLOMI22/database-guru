#!/bin/bash
# Run tests for Database Guru
# Usage: ./run_tests.sh [test_file]

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Database Guru - Test Runner${NC}"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Ensure pytest is installed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${BLUE}Installing dev dependencies...${NC}"
    pip install -r requirements-dev.txt
fi

# Run tests
if [ -z "$1" ]; then
    # Run all tests
    echo -e "${BLUE}Running all tests...${NC}"
    python -m pytest tests/ -v --tb=short
else
    # Run specific test file
    echo -e "${BLUE}Running tests in $1...${NC}"
    python -m pytest "$1" -v --tb=short
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
