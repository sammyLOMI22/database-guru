import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from src.services.llm_usage_tracker import LLMUsageTracker

@pytest.mark.asyncio
async def test_llm_usage_tracker_estimate_tokens():
    tracker = LLMUsageTracker()

    # Test empty text
    count, method = tracker.estimate_tokens("")
    assert count == 0
    assert method == "empty"

    # Test some text
    text = "Hello world"
    count, method = tracker.estimate_tokens(text)
    assert count > 0
    assert method in ["tiktoken", "estimated"]

@pytest.mark.asyncio
async def test_llm_usage_tracker_extract_tokens():
    tracker = LLMUsageTracker()

    # Test Ollama
    ollama_resp = {"prompt_eval_count": 10, "eval_count": 20}
    in_t, out_t = tracker.extract_tokens(ollama_resp, "ollama")
    assert in_t == 10
    assert out_t == 20

    # Test OpenAI
    openai_resp = {"usage": {"prompt_tokens": 15, "completion_tokens": 25}}
    in_t, out_t = tracker.extract_tokens(openai_resp, "openai")
    assert in_t == 15
    assert out_t == 25

@pytest.mark.asyncio
async def test_llm_usage_tracker_track_call(monkeypatch):
    tracker = LLMUsageTracker()
    db = AsyncMock()

    # Mock begin_nested() to return a proper async context manager
    @asynccontextmanager
    async def mock_begin_nested():
        yield
    db.begin_nested = mock_begin_nested

    # Mock LLMCostService.calculate_cost to avoid DB calls in unit test
    async def mock_calculate_cost(*args, **kwargs):
        return 0.0123

    monkeypatch.setattr("src.services.llm_cost_service.LLMCostService.calculate_cost", mock_calculate_cost)

    async with tracker.track_call(
        db=db,
        agent_type="test_agent",
        model_name="test_model",
        llm_method="generate",
        prompt="Test prompt",
        provider="ollama"
    ) as tracking:
        tracking.set_response("Test response", {"prompt_eval_count": 5, "eval_count": 5})

    assert db.add.called
    assert db.flush.called

    record = db.add.call_args[0][0]
    assert record.agent_type == "test_agent"
    assert record.model_name == "test_model"
    assert record.provider == "ollama"
    assert record.input_tokens == 5
    assert record.output_tokens == 5
    assert record.estimated_cost_usd == 0.0123
