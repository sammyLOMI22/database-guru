"""Test script to verify AgentTrace functionality"""
import asyncio
import json
from src.llm.self_correcting_agent import AgentTrace

def test_agent_trace():
    """Test that AgentTrace captures steps correctly"""
    trace = AgentTrace()

    # Simulate a query execution trace
    trace.add_step("analysis", "Analyzing question: Show all customers")
    trace.add_step("planning", "Query plan created (complexity: medium, confidence: 0.85)",
                   metadata={"complexity": "medium", "confidence": 0.85})
    trace.add_step("generation", "Generated SQL: SELECT * FROM customers")
    trace.add_step("execution", "Executing SQL query")
    trace.add_step("success", "Query executed successfully (rows: 10, time: 45.2ms)",
                   metadata={"row_count": 10, "execution_time_ms": 45.2})

    # Convert to dict
    trace_dict = trace.to_dict()

    # Print the trace
    print("=" * 80)
    print("AGENT TRACE TEST")
    print("=" * 80)
    print(json.dumps(trace_dict, indent=2))
    print("=" * 80)

    # Verify structure
    assert "steps" in trace_dict
    assert "total_elapsed_ms" in trace_dict
    assert "start_time" in trace_dict
    assert len(trace_dict["steps"]) == 5

    # Verify each step has required fields
    for step in trace_dict["steps"]:
        assert "timestamp" in step
        assert "elapsed_ms" in step
        assert "type" in step
        assert "message" in step
        assert "metadata" in step
        assert "icon" in step

    print("\n✅ All assertions passed!")
    print(f"   - {len(trace_dict['steps'])} steps captured")
    print(f"   - Total elapsed: {trace_dict['total_elapsed_ms']:.2f}ms")
    print(f"   - Start time: {trace_dict['start_time']}")

    # Test step types have correct icons
    step_types = {step["type"]: step["icon"] for step in trace_dict["steps"]}
    print(f"\n📋 Step type icons:")
    for step_type, icon in step_types.items():
        print(f"   {icon} {step_type}")

if __name__ == "__main__":
    test_agent_trace()
