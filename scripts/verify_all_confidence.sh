#!/bin/bash
# Comprehensive confidence scoring verification script
# Runs all verification tests in sequence

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════╗"
echo "║     Confidence Scoring Full Verification            ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

FAILED=0
START_TIME=$(date +%s)

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Test 1: Standalone verification
echo "═══════════════════════════════════════════════════════"
echo "  Test 1/3: Standalone Verification"
echo "═══════════════════════════════════════════════════════"
echo ""
python scripts/verify_confidence_scoring.py
if [ $? -ne 0 ]; then
    FAILED=$((FAILED + 1))
    echo ""
    echo "❌ Standalone verification failed"
else
    echo ""
    echo "✅ Standalone verification passed"
fi
echo ""

# Test 2: Unit tests
echo "═══════════════════════════════════════════════════════"
echo "  Test 2/3: Unit Tests"
echo "═══════════════════════════════════════════════════════"
echo ""
python -m pytest tests/test_confidence_scorer.py -v --tb=short
if [ $? -ne 0 ]; then
    FAILED=$((FAILED + 1))
    echo ""
    echo "❌ Unit tests failed"
else
    echo ""
    echo "✅ Unit tests passed"
fi
echo ""

# Test 3: Integration tests
echo "═══════════════════════════════════════════════════════"
echo "  Test 3/3: Integration Tests"
echo "═══════════════════════════════════════════════════════"
echo ""
python -m pytest tests/test_self_correcting_agent.py -v --tb=short
if [ $? -ne 0 ]; then
    FAILED=$((FAILED + 1))
    echo ""
    echo "❌ Integration tests failed"
else
    echo ""
    echo "✅ Integration tests passed"
fi
echo ""

# Calculate duration
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Summary
echo "╔══════════════════════════════════════════════════════╗"
echo "║               VERIFICATION SUMMARY                   ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "  ✅ Standalone Verification:  PASSED"
    echo "  ✅ Unit Tests (31 tests):    PASSED"
    echo "  ✅ Integration Tests (16):   PASSED"
    echo ""
    echo "  Total Duration: ${DURATION}s"
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║                                                      ║"
    echo "║  🎉 Confidence Scoring is fully functional! 🎉      ║"
    echo "║                                                      ║"
    echo "╚══════════════════════════════════════════════════════╝"
    exit 0
else
    echo "  ❌ $FAILED test suite(s) failed"
    echo ""
    echo "  Total Duration: ${DURATION}s"
    echo ""
    echo "⚠️  Please review the failed tests above"
    exit 1
fi
