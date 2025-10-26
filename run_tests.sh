#!/bin/bash
# Run tests for Database Guru
# Usage: ./run_tests.sh [test_file|feedback|all]
#
# Examples:
#   ./run_tests.sh                    # Run all tests
#   ./run_tests.sh feedback           # Run only feedback tests
#   ./run_tests.sh test_feedback_api.py  # Run specific test file

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Database Guru - Test Runner         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Set PYTHONPATH to project root (dynamically get current directory)
export PYTHONPATH="$(pwd)"

# Ensure pytest is installed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${BLUE}Installing dev dependencies...${NC}"
    pip install -r requirements-dev.txt
fi

# Run tests based on argument
if [ -z "$1" ]; then
    # Run all tests
    echo -e "${BLUE}Running all tests...${NC}"
    echo ""
    python -m pytest tests/ -v --tb=short
elif [ "$1" = "feedback" ]; then
    # Run only feedback system tests
    echo -e "${YELLOW}Running Feedback System Tests...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}📝 API Endpoint Tests${NC}"
    python -m pytest tests/test_feedback_api.py -v --tb=short
    echo ""
    echo -e "${BLUE}🔍 Validation Logic Tests${NC}"
    python -m pytest tests/test_feedback_validator.py -v --tb=short
    echo ""
    echo -e "${BLUE}🔗 Integration Tests${NC}"
    python -m pytest tests/test_feedback_integration.py -v --tb=short
elif [ "$1" = "all" ]; then
    # Run all tests with coverage
    echo -e "${BLUE}Running all tests with coverage report...${NC}"
    echo ""
    python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing --cov-report=html
    echo ""
    echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
else
    # Run specific test file
    echo -e "${BLUE}Running tests in $1...${NC}"
    echo ""
    python -m pytest "tests/$1" -v --tb=short
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
else
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ Some tests failed${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi
