#!/bin/bash
# Master script to run all tests: backend unit, integration, and frontend
# Usage: ./scripts/test_all.sh [--skip-frontend] [--skip-integration] [--coverage]

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_FRONTEND=false
SKIP_INTEGRATION=false
COVERAGE=false

for arg in "$@"; do
    case $arg in
        --skip-frontend)
            SKIP_FRONTEND=true
            ;;
        --skip-integration)
            SKIP_INTEGRATION=true
            ;;
        --coverage|-c)
            COVERAGE=true
            ;;
        --help|-h)
            echo "Usage: ./scripts/test_all.sh [OPTIONS]"
            echo ""
            echo "Run the complete test suite: backend unit, integration, and frontend tests."
            echo ""
            echo "Options:"
            echo "  --skip-frontend       Skip frontend tests"
            echo "  --skip-integration    Skip integration tests (no server needed)"
            echo "  --coverage, -c        Run backend tests with coverage"
            echo "  --help, -h            Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./scripts/test_all.sh                        # Run all tests"
            echo "  ./scripts/test_all.sh --skip-integration     # Skip integration tests"
            echo "  ./scripts/test_all.sh --coverage             # Run with coverage"
            echo "  ./scripts/test_all.sh --skip-frontend -c     # Backend only with coverage"
            exit 0
            ;;
    esac
done

echo -e "${MAGENTA}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                                                      ║${NC}"
echo -e "${MAGENTA}║        🧙‍♂️  DATABASE GURU TEST SUITE 🧙‍♂️             ║${NC}"
echo -e "${MAGENTA}║                                                      ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# Track results
BACKEND_STATUS="⏭️  SKIPPED"
INTEGRATION_STATUS="⏭️  SKIPPED"
FRONTEND_STATUS="⏭️  SKIPPED"
OVERALL_SUCCESS=true

START_TIME=$(date +%s)

# ============================================================================
# 1. Backend Unit Tests
# ============================================================================
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  STEP 1/3: Backend Unit Tests                         ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

BACKEND_CMD="./scripts/test_backend.sh"
if [ "$COVERAGE" = true ]; then
    BACKEND_CMD="$BACKEND_CMD --coverage"
fi

if $BACKEND_CMD; then
    BACKEND_STATUS="${GREEN}✅ PASSED${NC}"
else
    BACKEND_STATUS="${RED}❌ FAILED${NC}"
    OVERALL_SUCCESS=false
fi

echo ""

# ============================================================================
# 2. Integration Tests
# ============================================================================
if [ "$SKIP_INTEGRATION" = false ]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  STEP 2/3: Integration Tests                          ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""

    if ./scripts/test_integration.sh; then
        INTEGRATION_STATUS="${GREEN}✅ PASSED${NC}"
    else
        INTEGRATION_STATUS="${RED}❌ FAILED${NC}"
        OVERALL_SUCCESS=false
    fi

    echo ""
else
    echo -e "${YELLOW}⏭️  Skipping integration tests${NC}"
    echo ""
fi

# ============================================================================
# 3. Frontend Tests
# ============================================================================
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  STEP 3/3: Frontend Tests                             ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""

    if ./scripts/test_frontend.sh; then
        FRONTEND_STATUS="${GREEN}✅ PASSED${NC}"
    else
        FRONTEND_STATUS="${RED}❌ FAILED${NC}"
        OVERALL_SUCCESS=false
    fi

    echo ""
else
    echo -e "${YELLOW}⏭️  Skipping frontend tests${NC}"
    echo ""
fi

# ============================================================================
# Summary
# ============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "${MAGENTA}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                   TEST SUMMARY                       ║${NC}"
echo -e "${MAGENTA}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Backend Unit Tests:    $BACKEND_STATUS"
echo -e "  Integration Tests:     $INTEGRATION_STATUS"
echo -e "  Frontend Tests:        $FRONTEND_STATUS"
echo ""
echo -e "${BLUE}  Total Duration: ${DURATION}s${NC}"
echo ""

if [ "$OVERALL_SUCCESS" = true ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                      ║${NC}"
    echo -e "${GREEN}║            ✅  ALL TESTS PASSED! 🎉                  ║${NC}"
    echo -e "${GREEN}║                                                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                      ║${NC}"
    echo -e "${RED}║            ❌  SOME TESTS FAILED                     ║${NC}"
    echo -e "${RED}║                                                      ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
