"""Unit tests for CypherExplainer (Phase 25.4).

Tests cover:
* Successful explanation with LLM mock.
* Deterministic fallback when no LLM is available.
* Timeout and error fallback paths.
* Max output truncation.
* Factory wiring.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.neo4j.cypher_explainer import (
    CypherExplainer,
    CypherExplanationResult,
    _fallback_explanation,
    get_cypher_explainer,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


def _sample_schema():
    return {
        "labels": [
            {"name": "User"},
            {"name": "Order"},
        ],
        "relationships": [
            {"name": "PURCHASED"},
        ],
    }


def _make_client(response_text: str) -> MagicMock:
    client = MagicMock()
    client.generate = AsyncMock(return_value=response_text)
    client.provider_name = "ollama"
    return client


# ── fallback_explanation ─────────────────────────────────────────────────


class TestFallbackExplanation:
    def test_identifies_cypher_clauses(self):
        cypher = "MATCH (u:User)\nWHERE u.age > 18\nRETURN u\nLIMIT 10"
        result = _fallback_explanation(cypher)
        assert "MATCH" in result
        assert "WHERE" in result
        assert "RETURN" in result
        assert "LIMIT" in result

    def test_handles_empty_query(self):
        result = _fallback_explanation("")
        assert "could not be analyzed" in result

    def test_handles_unwind(self):
        cypher = "UNWIND [1,2,3] AS x\nRETURN x"
        result = _fallback_explanation(cypher)
        assert "UNWIND" in result

    def test_handles_optional_match(self):
        cypher = "MATCH (u:User)\nOPTIONAL MATCH (u)-[:FRIENDS]->(f)\nRETURN u, f"
        result = _fallback_explanation(cypher)
        assert "MATCH" in result
        assert "OPTIONAL MATCH" in result


# ── CypherExplainer ──────────────────────────────────────────────────────


class TestCypherExplainer:
    @pytest.mark.asyncio
    async def test_successful_explanation(self):
        explanation_text = (
            "This query finds all User nodes and returns them, limited to 10."
        )
        client = _make_client(explanation_text)
        explainer = CypherExplainer(client, model="llama3")
        result = await explainer.explain(
            "MATCH (u:User) RETURN u LIMIT 10",
            schema=_sample_schema(),
        )

        assert isinstance(result, CypherExplanationResult)
        assert result.explanation == explanation_text
        assert result.used_fallback is False
        assert result.model == "llama3"
        assert result.provider == "ollama"

    @pytest.mark.asyncio
    async def test_no_client_returns_fallback(self):
        explainer = CypherExplainer(None, model=None)
        result = await explainer.explain("MATCH (n) RETURN n LIMIT 10")

        assert result.used_fallback is True
        assert "MATCH" in result.explanation
        assert "RETURN" in result.explanation

    @pytest.mark.asyncio
    async def test_empty_response_returns_fallback(self):
        client = _make_client("")
        explainer = CypherExplainer(client, model="llama3")
        result = await explainer.explain("MATCH (n) RETURN n LIMIT 10")

        assert result.used_fallback is True

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self):
        import asyncio

        client = MagicMock()
        client.provider_name = "ollama"

        async def slow_generate(**kwargs):
            await asyncio.sleep(10)
            return "explanation"

        client.generate = slow_generate
        explainer = CypherExplainer(client, model="llama3", timeout_seconds=0.01)
        result = await explainer.explain("MATCH (n) RETURN n")

        assert result.used_fallback is True

    @pytest.mark.asyncio
    async def test_exception_returns_fallback(self):
        client = MagicMock()
        client.provider_name = "ollama"
        client.generate = AsyncMock(side_effect=RuntimeError("LLM down"))
        explainer = CypherExplainer(client, model="llama3")
        result = await explainer.explain("MATCH (n) RETURN n")

        assert result.used_fallback is True

    @pytest.mark.asyncio
    async def test_truncates_long_output(self):
        long_text = "A" * 2000
        client = _make_client(long_text)
        explainer = CypherExplainer(client, model="llama3", max_output_chars=500)
        result = await explainer.explain("MATCH (n) RETURN n")

        assert len(result.explanation) <= 501  # 500 + ellipsis char
        assert result.explanation.endswith("…")

    @pytest.mark.asyncio
    async def test_schema_context_passed_when_provided(self):
        client = _make_client("This finds users.")
        explainer = CypherExplainer(client, model="llama3")
        result = await explainer.explain(
            "MATCH (u:User) RETURN u",
            schema=_sample_schema(),
        )

        call_kwargs = client.generate.call_args
        prompt = call_kwargs.kwargs.get("prompt", "")
        assert "User" in prompt
        assert "PURCHASED" in prompt
        assert result.used_fallback is False


# ── Factory ──────────────────────────────────────────────────────────────


class TestGetCypherExplainer:
    @pytest.mark.asyncio
    async def test_factory_returns_explainer(self):
        with patch("src.llm.get_llm_client") as mock_get:
            mock_get.return_value = MagicMock()
            explainer = await get_cypher_explainer(db_session=None)
            assert isinstance(explainer, CypherExplainer)

    @pytest.mark.asyncio
    async def test_factory_with_db_session(self):
        mock_router = MagicMock()
        mock_router.get_model_for_task.return_value = "claude-3"
        mock_router.get_timeout_for_task.return_value = 20
        mock_router.get_provider_for_task.return_value = "anthropic"

        with patch("src.llm.get_llm_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch(
                "src.llm.model_router.get_model_router",
                new=AsyncMock(return_value=mock_router),
            ):
                explainer = await get_cypher_explainer(db_session=MagicMock())
                assert explainer.model == "claude-3"
                assert explainer.timeout_seconds == 20.0
