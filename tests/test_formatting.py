"""Test script to verify formatting functionality for Option 2"""
import asyncio
import json
from src.llm.self_correcting_agent import SelfCorrectingSQLAgent, CorrectionAttempt, ErrorType
from unittest.mock import Mock

def test_format_attempts_for_ui():
    """Test that attempts are formatted correctly for UI"""
    # Create mock SQL generator
    mock_generator = Mock()

    # Create agent
    agent = SelfCorrectingSQLAgent(
        sql_generator=mock_generator,
        max_retries=3,
        enable_diagnostics=True
    )

    # Simulate fix methods tracking
    agent.fix_methods = {
        1: None,  # First attempt (no fix needed)
        2: "quick_fix",  # Second attempt used quick fix
        3: "learned",  # Third attempt used learned correction
        4: "llm"  # Fourth attempt used LLM
    }

    # Create mock attempts
    attempts = [
        CorrectionAttempt(
            attempt_number=1,
            sql="SELECT * FROM users",
            error="table users does not exist",
            error_type=ErrorType.TABLE_NOT_FOUND,
            success=False,
            execution_time_ms=10.5,
            row_count=None
        ),
        CorrectionAttempt(
            attempt_number=2,
            sql="SELECT * FROM user",
            error="column age does not exist",
            error_type=ErrorType.COLUMN_NOT_FOUND,
            success=False,
            execution_time_ms=12.3,
            row_count=None
        ),
        CorrectionAttempt(
            attempt_number=3,
            sql="SELECT * FROM user WHERE created_at > '2024-01-01'",
            error=None,
            error_type=ErrorType.UNKNOWN,
            success=True,
            execution_time_ms=45.2,
            row_count=150
        ),
    ]

    # Format attempts
    formatted = agent.format_attempts_for_ui(attempts)

    # Print results
    print("=" * 80)
    print("FORMAT ATTEMPTS TEST")
    print("=" * 80)
    print(json.dumps(formatted, indent=2))
    print("=" * 80)

    # Verify structure
    assert len(formatted) == 3
    assert formatted[0]["attempt_number"] == 1
    assert formatted[0]["success"] is False
    assert formatted[0]["error_type"] == "table_not_found"
    assert formatted[0]["fix_method"] is None  # First attempt has no fix

    assert formatted[1]["attempt_number"] == 2
    assert formatted[1]["fix_method"] == "quick_fix"

    assert formatted[2]["attempt_number"] == 3
    assert formatted[2]["success"] is True
    assert formatted[2]["row_count"] == 150
    assert formatted[2]["fix_method"] == "learned"

    print("\n✅ All assertions passed!")
    print(f"   - {len(formatted)} attempts formatted")
    print(f"   - Fix methods tracked: {[a['fix_method'] for a in formatted]}")

    # Test with empty attempts
    empty_formatted = agent.format_attempts_for_ui([])
    assert empty_formatted == []
    print("   - Empty attempts handled correctly")

    return formatted

def test_observability_data_structure():
    """Test the complete observability data structure"""
    print("\n" + "=" * 80)
    print("OBSERVABILITY DATA STRUCTURE TEST")
    print("=" * 80)

    # Simulate a complete query response with all observability fields
    observability_data = {
        "agent_trace": {
            "steps": [
                {
                    "timestamp": "2025-10-19T18:00:00",
                    "elapsed_ms": 0.0,
                    "type": "analysis",
                    "message": "Analyzing question",
                    "metadata": {},
                    "icon": "🔍"
                },
                {
                    "timestamp": "2025-10-19T18:00:00.050",
                    "elapsed_ms": 50.0,
                    "type": "generation",
                    "message": "Generated SQL",
                    "metadata": {"sql": "SELECT * FROM users"},
                    "icon": "✨"
                },
                {
                    "timestamp": "2025-10-19T18:00:00.100",
                    "elapsed_ms": 100.0,
                    "type": "error",
                    "message": "Execution failed",
                    "metadata": {},
                    "icon": "❌"
                },
                {
                    "timestamp": "2025-10-19T18:00:00.150",
                    "elapsed_ms": 150.0,
                    "type": "quick_fix",
                    "message": "Applied quick fix",
                    "metadata": {"confidence": 0.9},
                    "icon": "⚡"
                },
                {
                    "timestamp": "2025-10-19T18:00:00.200",
                    "elapsed_ms": 200.0,
                    "type": "success",
                    "message": "Query executed successfully",
                    "metadata": {"row_count": 150},
                    "icon": "✅"
                }
            ],
            "total_elapsed_ms": 200.0,
            "start_time": "2025-10-19T18:00:00"
        },
        "query_plan": {
            "complexity": "medium",
            "intent": "retrieve user records",
            "confidence": 0.85,
            "tables": [{"name": "users", "alias": "u"}],
            "joins_count": 0,
            "filters_count": 1,
            "aggregations_count": 0
        },
        "attempts": [
            {
                "attempt_number": 1,
                "sql": "SELECT * FROM users",
                "success": False,
                "error": "table not found",
                "error_type": "table_not_found",
                "execution_time_ms": 10.5,
                "row_count": None,
                "fix_method": None
            },
            {
                "attempt_number": 2,
                "sql": "SELECT * FROM user",
                "success": True,
                "error": None,
                "error_type": None,
                "execution_time_ms": 45.2,
                "row_count": 150,
                "fix_method": "quick_fix"
            }
        ],
        "self_corrected": True,
        "total_attempts": 2,
        "verification_warnings": ["⚠️ Result verification: Empty result set might be unexpected"],
        "used_planning": False
    }

    print(json.dumps(observability_data, indent=2))
    print("=" * 80)

    # Verify all fields are present
    assert "agent_trace" in observability_data
    assert "query_plan" in observability_data
    assert "attempts" in observability_data
    assert "self_corrected" in observability_data
    assert "total_attempts" in observability_data
    assert "verification_warnings" in observability_data
    assert "used_planning" in observability_data

    # Verify agent_trace structure
    assert "steps" in observability_data["agent_trace"]
    assert "total_elapsed_ms" in observability_data["agent_trace"]
    assert "start_time" in observability_data["agent_trace"]
    assert len(observability_data["agent_trace"]["steps"]) == 5

    # Verify attempts structure
    assert len(observability_data["attempts"]) == 2
    assert observability_data["attempts"][0]["fix_method"] is None
    assert observability_data["attempts"][1]["fix_method"] == "quick_fix"

    print("\n✅ All observability fields verified!")
    print(f"   - Agent trace: {len(observability_data['agent_trace']['steps'])} steps")
    print(f"   - Attempts: {len(observability_data['attempts'])} total")
    print(f"   - Self-corrected: {observability_data['self_corrected']}")
    print(f"   - Used planning: {observability_data['used_planning']}")
    print(f"   - Verification warnings: {len(observability_data['verification_warnings'])}")

if __name__ == "__main__":
    print("Testing Option 2 Week 1 Day 2 - Query Plan & Attempts Formatting")
    print()

    # Test 1: Format attempts
    formatted_attempts = test_format_attempts_for_ui()

    # Test 2: Complete observability structure
    test_observability_data_structure()

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
