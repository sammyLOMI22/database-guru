#!/usr/bin/env python3
"""
Integration Test for Confidence Scoring with Self-Correcting Agent

This script verifies that confidence scores appear in actual correction attempts.
"""
import asyncio
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.self_correcting_agent import SelfCorrectingSQLAgent, ErrorDiagnostics
from src.llm.sql_generator import SQLGenerator
from src.config.settings import Settings
from unittest.mock import Mock, AsyncMock


async def test_confidence_in_correction_attempts():
    """Test that confidence scores appear in correction attempts"""
    print("\n" + "="*70)
    print("  Testing Confidence Scoring Integration")
    print("="*70 + "\n")

    # Create mock generator
    generator = Mock(spec=SQLGenerator)
    generator.settings = Settings()

    # Mock generate_sql to return SQL with typo
    async def mock_generate(*args, **kwargs):
        return {
            "sql": "SELECT * FROM custmers",  # Intentional typo
            "confidence": 0.85,
            "is_valid": True
        }
    generator.generate_sql = mock_generate

    # Mock fix_sql_error to return corrected SQL
    async def mock_fix(*args, **kwargs):
        return {
            "sql": "SELECT * FROM customers",  # Fixed typo
            "confidence": 0.90
        }
    generator.fix_sql_error = mock_fix

    # Create agent
    agent = SelfCorrectingSQLAgent(
        sql_generator=generator,
        max_retries=3,
        enable_diagnostics=True,
        enable_learning=False,  # Disable to avoid DB dependency
        enable_schema_fixes=False  # Disable to avoid schema parsing
    )

    # Mock database session
    mock_session = Mock()

    # Create mock executor that fails first, succeeds second
    attempt_count = 0

    async def mock_execute_side_effect(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1

        if attempt_count == 1:
            # First attempt fails
            return {
                "success": False,
                "error": 'relation "custmers" does not exist',
                "execution_time_ms": 10
            }
        else:
            # Second attempt succeeds
            return {
                "success": True,
                "result": [{"id": 1, "name": "Test"}],
                "row_count": 1,
                "execution_time_ms": 15
            }

    # Patch the executor
    from src.core import executor as executor_module
    original_execute = executor_module.SQLExecutor.execute_query
    executor_module.SQLExecutor.execute_query = mock_execute_side_effect

    try:
        # Run the agent
        result = await agent.generate_and_execute_with_retry(
            question="Show all customers",
            schema='{"customers": ["id", "name", "email"]}',
            session=mock_session,
            database_type="postgresql",
            schema_dict={"customers": ["id", "name", "email"]}
        )

        print("✅ Agent execution completed\n")

        # Check results
        print(f"Success: {result.get('success')}")
        print(f"Total Attempts: {result.get('total_attempts')}")
        print(f"Self-Corrected: {result.get('self_corrected')}")

        # Check for confidence scores in attempts
        attempts = result.get("attempts", [])
        print(f"\nAttempts: {len(attempts)}")

        for i, attempt in enumerate(attempts, 1):
            print(f"\n--- Attempt {i} ---")
            print(f"  SQL: {attempt.sql[:50]}...")
            print(f"  Success: {attempt.success}")
            print(f"  Error Type: {attempt.error_type.value if attempt.error_type else None}")

            if attempt.confidence_score:
                print(f"  ✅ Confidence Score Present!")
                print(f"     Confidence: {attempt.confidence_score['confidence']:.1%}")
                print(f"     Level: {attempt.confidence_score['level']}")
                print(f"     Recommendation: {attempt.confidence_score['recommendation'][:50]}...")
                print(f"     Reasoning: {attempt.confidence_score['reasoning'][:80]}...")

                # Verify structure
                required_keys = ['confidence', 'factors', 'reasoning', 'recommendation', 'level']
                for key in required_keys:
                    assert key in attempt.confidence_score, f"Missing key: {key}"

            else:
                if i > 1:  # Only corrections (attempt 2+) should have confidence
                    print(f"  ⚠️  No confidence score (expected for corrections)")
                else:
                    print(f"  ℹ️  No confidence score (first attempt - expected)")

        # Verify at least one attempt has confidence score
        has_confidence = any(a.confidence_score is not None for a in attempts)

        if has_confidence:
            print("\n✅ SUCCESS: Confidence scores are present in correction attempts!")
            return True
        else:
            print("\n⚠️  WARNING: No confidence scores found in attempts")
            return False

    finally:
        # Restore original executor
        executor_module.SQLExecutor.execute_query = original_execute


async def test_confidence_in_formatted_attempts():
    """Test that confidence scores appear in UI-formatted attempts"""
    print("\n" + "="*70)
    print("  Testing Confidence in Formatted Output")
    print("="*70 + "\n")

    # Create mock generator
    generator = Mock(spec=SQLGenerator)
    generator.settings = Settings()

    async def mock_fix(*args, **kwargs):
        return {"sql": "SELECT * FROM customers", "confidence": 0.90}
    generator.fix_sql_error = mock_fix

    # Create agent
    agent = SelfCorrectingSQLAgent(
        sql_generator=generator,
        enable_learning=False
    )

    # Create mock attempts with confidence scores
    from src.llm.self_correcting_agent import CorrectionAttempt, ErrorType

    attempts = [
        CorrectionAttempt(
            attempt_number=1,
            sql="SELECT * FROM custmers",
            error='relation "custmers" does not exist',
            error_type=ErrorType.TABLE_NOT_FOUND,
            success=False,
            execution_time_ms=10,
            row_count=0,
            confidence_score=None  # First attempt has no confidence
        ),
        CorrectionAttempt(
            attempt_number=2,
            sql="SELECT * FROM customers",
            error=None,
            error_type=ErrorType.UNKNOWN,
            success=True,
            execution_time_ms=15,
            row_count=1,
            confidence_score={
                "confidence": 0.873,
                "level": "HIGH",
                "factors": {
                    "error_type": 0.255,
                    "schema_match": 0.218,
                    "historical_success": 0.174,
                    "correction_complexity": 0.131,
                    "similarity": 0.095
                },
                "reasoning": "This correction has high confidence (87.3%)...",
                "recommendation": "EXECUTE - High confidence, likely to succeed"
            }
        )
    ]

    # Format for UI
    formatted = agent.format_attempts_for_ui(attempts)

    print("Formatted Attempts:")
    print(json.dumps(formatted, indent=2))

    # Verify confidence_prediction is present
    assert "confidence_prediction" in formatted[1], "Missing confidence_prediction in formatted output"
    assert formatted[1]["confidence_prediction"]["confidence"] == 0.873

    print("\n✅ SUCCESS: Confidence scores appear in formatted output!")
    return True


async def main():
    """Run all integration tests"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║      Confidence Scoring Integration Verification                  ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    results = []

    # Test 1: Confidence in correction attempts
    try:
        result = await test_confidence_in_correction_attempts()
        results.append(("Correction Attempts", result))
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("Correction Attempts", False))

    # Test 2: Confidence in formatted output
    try:
        result = await test_confidence_in_formatted_attempts()
        results.append(("Formatted Output", result))
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append(("Formatted Output", False))

    # Summary
    print("\n" + "="*70)
    print("  INTEGRATION TEST SUMMARY")
    print("="*70 + "\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("   Confidence scoring is fully integrated and working!\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed\n")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
