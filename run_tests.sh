#!/bin/bash
# Run tests for Database Guru
# Usage: ./run_tests.sh [category|test_file|all]
#
# Examples:
#   ./run_tests.sh                    # Run all tests
#   ./run_tests.sh --list             # List all available tests and categories
#   ./run_tests.sh feedback           # Run only feedback tests
#   ./run_tests.sh parallel           # Run parallel execution tests
#   ./run_tests.sh security           # Run security tests
#   ./run_tests.sh test_feedback_api.py  # Run specific test file
#   ./run_tests.sh all                # Run all tests with coverage

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Database Guru - Test Runner         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Function to list all available tests and categories
list_tests() {
    echo -e "${CYAN}Available Test Categories:${NC}"
    echo -e "  ${YELLOW}core${NC}         - Core/Unit tests (db, models, schema, executor)"
    echo -e "  ${YELLOW}agents${NC}       - Agent tests (self-correcting, query planning, confidence)"
    echo -e "  ${YELLOW}api${NC}          - API endpoint tests"
    echo -e "  ${YELLOW}feedback${NC}     - Feedback system tests"
    echo -e "  ${YELLOW}parallel${NC}     - Parallel execution tests"
    echo -e "  ${YELLOW}streaming${NC}    - Streaming response tests"
    echo -e "  ${YELLOW}cache${NC}        - Caching tests (Redis, semantic)"
    echo -e "  ${YELLOW}mapping${NC}      - Mapping/Learning tests (column, table, patterns)"
    echo -e "  ${YELLOW}security${NC}     - Security tests (prompt sanitizer)"
    echo -e "  ${YELLOW}tools${NC}        - Tools tests (index advisor, index tools)"
    echo -e "  ${YELLOW}cleanup${NC}      - Cleanup tests (session/history deletion)"
    echo -e "  ${YELLOW}integration${NC}  - End-to-end integration tests"
    echo -e "  ${YELLOW}all${NC}          - All tests with coverage"
    echo ""
    echo -e "${CYAN}Available Test Files:${NC}"
    for test_file in tests/test_*.py; do
        test_name=$(basename "$test_file")
        echo -e "  ${GREEN}${test_name}${NC}"
    done
    echo ""
    echo -e "${CYAN}Usage:${NC}"
    echo -e "  ./run_tests.sh [category|test_file]"
    echo -e "  ./run_tests.sh --list (show this help)"
    echo ""
}

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

# Parse command line arguments
CATEGORY="${1:-all-basic}"

# Handle --list or -l flag
if [ "$CATEGORY" = "--list" ] || [ "$CATEGORY" = "-l" ] || [ "$CATEGORY" = "list" ]; then
    list_tests
    exit 0
fi

# Run tests based on category or argument
case "$CATEGORY" in
    "core")
        echo -e "${YELLOW}Running Core/Unit Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_db_connection.py \
                        tests/test_llm.py \
                        tests/test_duckdb_connection.py \
                        tests/test_models.py \
                        tests/test_executor.py \
                        tests/test_schema_validator.py \
                        tests/test_schema_sampling.py \
                        tests/test_schema_validation_standalone.py \
                        tests/test_schema_cache.py \
                        tests/test_agent_trace.py \
                        tests/test_formatting.py \
                        -v --tb=short
        ;;

    "agents")
        echo -e "${YELLOW}Running Agent Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_self_correcting_agent.py \
                        tests/test_schema_aware_fixer.py \
                        tests/test_confidence_scorer.py \
                        tests/test_correction_learner.py \
                        tests/test_query_planning_agent.py \
                        tests/test_result_verification_agent.py \
                        -v --tb=short
        ;;

    "api")
        echo -e "${YELLOW}Running API/Endpoint Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_api.py \
                        tests/test_query_endpoints.py \
                        tests/test_conversation_api.py \
                        tests/test_feedback_api.py \
                        tests/test_streaming_api.py \
                        tests/test_multi_db_streaming_api.py \
                        tests/test_mappings_api.py \
                        tests/test_cache_endpoints.py \
                        tests/test_index_recommendations_api.py \
                        -v --tb=short
        ;;

    "feedback")
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
        ;;

    "parallel")
        echo -e "${YELLOW}Running Parallel Execution Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_parallel_corrections.py \
                        tests/test_parallel_multi_db.py \
                        -v --tb=short
        ;;

    "streaming")
        echo -e "${YELLOW}Running Streaming Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_streaming.py \
                        tests/test_streaming_api.py \
                        tests/test_multi_db_streaming_api.py \
                        -v --tb=short
        ;;

    "cache")
        echo -e "${YELLOW}Running Cache Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_redis_cache.py \
                        tests/test_semantic_caching.py \
                        tests/test_cache_endpoints.py \
                        -v --tb=short
        ;;

    "mapping")
        echo -e "${YELLOW}Running Mapping/Learning Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_column_mapper.py \
                        tests/test_table_mapper.py \
                        tests/test_result_pattern_learner.py \
                        tests/test_mapping_cache.py \
                        -v --tb=short
        ;;

    "security")
        echo -e "${YELLOW}Running Security Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_prompt_sanitizer.py -v --tb=short
        ;;

    "tools")
        echo -e "${YELLOW}Running Tools Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_tools.py \
                        tests/test_index_advisor.py \
                        tests/test_index_tools.py \
                        -v --tb=short
        ;;

    "cleanup")
        echo -e "${YELLOW}Running Cleanup Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_chat_session_deletion.py \
                        tests/test_query_history_deletion.py \
                        -v --tb=short
        ;;

    "integration")
        echo -e "${YELLOW}Running Integration Tests...${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        python -m pytest tests/test_end_to_end.py \
                        tests/test_multi_db.py \
                        tests/test_conversational_memory.py \
                        -v --tb=short
        ;;

    "all")
        echo -e "${BLUE}Running all tests with coverage report...${NC}"
        echo ""
        python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing --cov-report=html
        echo ""
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    "all-basic"|"")
        echo -e "${BLUE}Running all tests...${NC}"
        echo ""
        python -m pytest tests/ -v --tb=short
        ;;

    test_*.py)
        # Run specific test file
        echo -e "${BLUE}Running tests in $CATEGORY...${NC}"
        echo ""
        python -m pytest "tests/$CATEGORY" -v --tb=short
        ;;

    *)
        # Try to run it as a test file if it exists
        if [ -f "tests/test_$CATEGORY.py" ]; then
            echo -e "${BLUE}Running tests in test_$CATEGORY.py...${NC}"
            echo ""
            python -m pytest "tests/test_$CATEGORY.py" -v --tb=short
        elif [ -f "tests/$CATEGORY" ]; then
            echo -e "${BLUE}Running tests in $CATEGORY...${NC}"
            echo ""
            python -m pytest "tests/$CATEGORY" -v --tb=short
        else
            echo -e "${RED}Unknown test category or file: $CATEGORY${NC}"
            echo ""
            echo -e "Use ${YELLOW}./run_tests.sh --list${NC} to see available categories and test files"
            exit 1
        fi
        ;;
esac

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
