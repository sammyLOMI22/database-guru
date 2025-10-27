#!/usr/bin/env python3
"""
Verification Script for Confidence Scoring Feature

This script tests the confidence scoring system to verify it's working correctly.
Runs through various scenarios and validates the predictions.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.confidence_scorer import get_confidence_scorer, ConfidenceScore


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_confidence(label: str, confidence: ConfidenceScore):
    """Print confidence score details"""
    print(f"🎯 {label}")
    print(f"   Confidence: {confidence.overall:.1%} ({confidence.get_level()})")
    print(f"   Recommendation: {confidence.recommendation}")
    print(f"   Reasoning: {confidence.reasoning}")
    print(f"   Factors:")
    for factor, score in confidence.factors.items():
        print(f"     - {factor}: {score:.3f}")
    print()


def test_basic_confidence_scoring():
    """Test 1: Basic confidence scoring"""
    print_section("TEST 1: Basic Confidence Scoring")

    scorer = get_confidence_scorer()

    # Test 1a: High confidence - simple typo fix
    print("✅ Test 1a: High Confidence - Table Typo Fix")
    confidence = scorer.predict_success_probability(
        error_type="table_not_found",
        original_sql="SELECT * FROM custmers WHERE state = 'CA'",
        correction_sql="SELECT * FROM customers WHERE state = 'CA'",
        schema={"customers": ["id", "name", "email", "state"]}
    )
    print_confidence("Simple table typo fix", confidence)
    assert confidence.overall >= 0.70, f"Expected high confidence, got {confidence.overall:.1%}"
    assert confidence.get_level() in ["HIGH", "MEDIUM"], f"Expected HIGH or MEDIUM, got {confidence.get_level()}"
    print("✅ PASSED: High confidence for simple typo\n")

    # Test 1b: Medium confidence - column fix
    print("✅ Test 1b: Medium Confidence - Column Fix")
    confidence = scorer.predict_success_probability(
        error_type="column_not_found",
        original_sql="SELECT customer_name FROM customers",
        correction_sql="SELECT name FROM customers",
        schema={"customers": ["id", "name", "email"]}
    )
    print_confidence("Column name fix", confidence)
    assert 0.40 <= confidence.overall <= 0.95, f"Expected medium range, got {confidence.overall:.1%}"
    print("✅ PASSED: Medium confidence for column fix\n")

    # Test 1c: Low confidence - infrastructure issue
    print("✅ Test 1c: Low Confidence - Infrastructure Issue")
    confidence = scorer.predict_success_probability(
        error_type="connection_error",
        original_sql="SELECT * FROM users",
        correction_sql="SELECT * FROM users WITH (NOLOCK)"
    )
    print_confidence("Connection error fix", confidence)
    assert confidence.overall < 0.60, f"Expected low confidence, got {confidence.overall:.1%}"
    print("✅ PASSED: Low confidence for infrastructure issue\n")


def test_schema_matching():
    """Test 2: Schema matching affects confidence"""
    print_section("TEST 2: Schema Matching")

    scorer = get_confidence_scorer()
    schema = {
        "customers": ["id", "name", "email", "state"],
        "orders": ["id", "customer_id", "total", "created_at"]
    }

    # Test 2a: Valid table in schema
    print("✅ Test 2a: Valid Table in Schema")
    confidence_valid = scorer.predict_success_probability(
        error_type="table_not_found",
        original_sql="SELECT * FROM custmers",
        correction_sql="SELECT * FROM customers",
        schema=schema
    )
    print_confidence("Fix to valid table", confidence_valid)

    # Test 2b: Invalid table not in schema
    print("✅ Test 2b: Invalid Table Not in Schema")
    confidence_invalid = scorer.predict_success_probability(
        error_type="table_not_found",
        original_sql="SELECT * FROM custmers",
        correction_sql="SELECT * FROM nonexistent_table",
        schema=schema
    )
    print_confidence("Fix to invalid table", confidence_invalid)

    assert confidence_valid.overall > confidence_invalid.overall, \
        "Valid table should have higher confidence than invalid table"
    print("✅ PASSED: Schema matching affects confidence correctly\n")


def test_historical_learning():
    """Test 3: Historical learning improves predictions"""
    print_section("TEST 3: Historical Learning")

    scorer = get_confidence_scorer()

    # Test 3a: Record successful corrections
    print("✅ Test 3a: Recording Successful Corrections")
    for i in range(8):
        scorer.update_historical_stats("table_not_found", success=True)
    for i in range(2):
        scorer.update_historical_stats("table_not_found", success=False)

    stats = scorer.get_stats()
    print(f"   Historical Stats for 'table_not_found':")
    print(f"   - Attempts: {stats['table_not_found']['attempts']}")
    print(f"   - Successes: {stats['table_not_found']['successes']}")
    print(f"   - Success Rate: {stats['table_not_found']['success_rate']:.1%}")
    assert stats['table_not_found']['success_rate'] == 0.8, "Expected 80% success rate"
    print("✅ PASSED: Historical stats recorded correctly\n")

    # Test 3b: Prediction uses historical data
    print("✅ Test 3b: Prediction Uses Historical Data")
    confidence = scorer.predict_success_probability(
        error_type="table_not_found",
        original_sql="SELECT * FROM ordes",
        correction_sql="SELECT * FROM orders"
    )
    print_confidence("Prediction with historical data", confidence)
    assert confidence.overall >= 0.50, "Historical success should boost confidence"
    print("✅ PASSED: Historical learning works\n")


def test_correction_complexity():
    """Test 4: Correction complexity affects confidence"""
    print_section("TEST 4: Correction Complexity")

    scorer = get_confidence_scorer()
    schema = {"customers": ["id", "name", "email"], "orders": ["id", "customer_id", "total"]}

    # Test 4a: Simple correction
    print("✅ Test 4a: Simple Correction (1-2 changes)")
    confidence_simple = scorer.predict_success_probability(
        error_type="syntax_error",
        original_sql="SELECT * FROM customers WHERE state = CA",
        correction_sql="SELECT * FROM customers WHERE state = 'CA'",
        schema=schema
    )
    print_confidence("Simple fix (add quotes)", confidence_simple)

    # Test 4b: Complex correction
    print("✅ Test 4b: Complex Correction (major rewrite)")
    confidence_complex = scorer.predict_success_probability(
        error_type="syntax_error",
        original_sql="SELECT * FROM customers",
        correction_sql="""
            SELECT c.name, COUNT(o.id) as order_count
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id
            GROUP BY c.name
            HAVING COUNT(o.id) > 5
        """,
        schema=schema
    )
    print_confidence("Complex rewrite", confidence_complex)

    assert confidence_simple.overall > confidence_complex.overall, \
        "Simple corrections should have higher confidence than complex rewrites"
    print("✅ PASSED: Correction complexity affects confidence correctly\n")


def test_confidence_to_dict():
    """Test 5: Confidence score serialization"""
    print_section("TEST 5: JSON Serialization")

    scorer = get_confidence_scorer()
    confidence = scorer.predict_success_probability(
        error_type="table_not_found",
        original_sql="SELECT * FROM users",
        correction_sql="SELECT * FROM customers",
        schema={"customers": ["id", "name"]}
    )

    # Test serialization
    result = confidence.to_dict()
    print("✅ Test 5a: Serialization to Dictionary")
    print(f"   Keys: {list(result.keys())}")

    required_keys = ["confidence", "factors", "reasoning", "recommendation", "level"]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"
    print(f"✅ PASSED: All required keys present\n")

    # Test JSON serialization
    print("✅ Test 5b: JSON Serialization")
    import json
    json_str = json.dumps(result)
    loaded = json.loads(json_str)
    assert loaded["confidence"] == result["confidence"]
    print("✅ PASSED: JSON serialization works\n")


def test_confidence_levels():
    """Test 6: Confidence levels are correct"""
    print_section("TEST 6: Confidence Levels")

    scorer = get_confidence_scorer()

    test_cases = [
        ("connection_error", 0.0, 0.50, ["LOW", "VERY_LOW", "MEDIUM"]),
        ("table_not_found", 0.70, 1.0, ["HIGH", "MEDIUM"]),
        ("syntax_error", 0.30, 0.80, ["HIGH", "MEDIUM", "LOW"]),
    ]

    for error_type, min_conf, max_conf, valid_levels in test_cases:
        confidence = scorer.predict_success_probability(
            error_type=error_type,
            original_sql="SELECT * FROM users",
            correction_sql="SELECT * FROM customers"
        )
        print(f"✅ {error_type}: {confidence.overall:.1%} ({confidence.get_level()})")
        assert min_conf <= confidence.overall <= max_conf, \
            f"Confidence {confidence.overall:.1%} not in expected range [{min_conf:.1%}, {max_conf:.1%}]"
        assert confidence.get_level() in valid_levels, \
            f"Level {confidence.get_level()} not in valid levels {valid_levels}"

    print("\n✅ PASSED: All confidence levels correct\n")


def test_singleton_pattern():
    """Test 7: Singleton pattern works"""
    print_section("TEST 7: Singleton Pattern")

    scorer1 = get_confidence_scorer()
    scorer2 = get_confidence_scorer()

    print(f"   Scorer 1 ID: {id(scorer1)}")
    print(f"   Scorer 2 ID: {id(scorer2)}")

    assert scorer1 is scorer2, "Scorers should be the same instance"
    print("✅ PASSED: Singleton pattern works\n")


def test_error_handling():
    """Test 8: Error handling"""
    print_section("TEST 8: Error Handling")

    scorer = get_confidence_scorer()

    # Test 8a: Unknown error type
    print("✅ Test 8a: Unknown Error Type")
    confidence = scorer.predict_success_probability(
        error_type="completely_unknown_error_type",
        original_sql="SELECT * FROM users",
        correction_sql="SELECT * FROM customers"
    )
    print_confidence("Unknown error type", confidence)
    assert 0.0 <= confidence.overall <= 1.0, "Should handle unknown error types gracefully"
    print("✅ PASSED: Unknown error types handled\n")

    # Test 8b: No schema provided
    print("✅ Test 8b: No Schema Provided")
    confidence = scorer.predict_success_probability(
        error_type="table_not_found",
        original_sql="SELECT * FROM users",
        correction_sql="SELECT * FROM customers",
        schema=None
    )
    print_confidence("No schema", confidence)
    assert 0.0 <= confidence.overall <= 1.0, "Should handle missing schema gracefully"
    print("✅ PASSED: Missing schema handled\n")

    # Test 8c: Identical SQL (no change)
    print("✅ Test 8c: Identical SQL (no change)")
    confidence = scorer.predict_success_probability(
        error_type="syntax_error",
        original_sql="SELECT * FROM customers",
        correction_sql="SELECT * FROM customers"
    )
    print_confidence("No change", confidence)
    assert confidence.overall < 0.9, "Should be skeptical of no-change corrections"
    print("✅ PASSED: No-change penalty applied\n")


def run_all_tests():
    """Run all verification tests"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║           Confidence Scoring Verification Tests                   ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    tests = [
        ("Basic Confidence Scoring", test_basic_confidence_scoring),
        ("Schema Matching", test_schema_matching),
        ("Historical Learning", test_historical_learning),
        ("Correction Complexity", test_correction_complexity),
        ("JSON Serialization", test_confidence_to_dict),
        ("Confidence Levels", test_confidence_levels),
        ("Singleton Pattern", test_singleton_pattern),
        ("Error Handling", test_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ FAILED: {test_name}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()

    # Summary
    print_section("TEST SUMMARY")
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Confidence scoring is working correctly.\n")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
