"""Unit tests for CypherGenerator (Phase 25.4).

Tests cover:
* Successful generation with LLM mock.
* Markdown fence stripping.
* LIMIT injection when the model forgets.
* Unknown label detection.
* Timeout and error fallback paths.
* Factory wiring.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.neo4j.cypher_generator import (
    CypherGenerator,
    CypherGenerationResult,
    _clean_cypher,
    _detect_unknown_labels,
    _inject_limit,
    get_cypher_generator,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


def _sample_schema():
    return {
        "labels": [
            {"name": "User", "estimated_count": 100, "properties": [
                {"name": "email", "types": ["String"]},
                {"name": "name", "types": ["String"]},
            ]},
            {"name": "Order", "estimated_count": 50, "properties": [
                {"name": "total", "types": ["Float"]},
            ]},
        ],
        "relationships": [
            {"name": "PURCHASED", "properties": []},
            {"name": "REVIEWED", "properties": []},
        ],
        "patterns": [
            {
                "source_labels": ["User"],
                "relationship_type": "PURCHASED",
                "target_labels": ["Order"],
                "estimated_count": 50,
            },
        ],
        "indexes": [],
    }


def _make_client(response_text: str) -> MagicMock:
    client = MagicMock()
    client.generate = AsyncMock(return_value=response_text)
    client.provider_name = "ollama"
    return client


# ── clean_cypher ─────────────────────────────────────────────────────────


class TestCleanCypher:
    def test_strips_markdown_fences(self):
        raw = "```cypher\nMATCH (n) RETURN n\n```"
        assert _clean_cypher(raw) == "MATCH (n) RETURN n"

    def test_strips_triple_backtick_no_lang(self):
        raw = "```\nMATCH (n) RETURN n\n```"
        assert _clean_cypher(raw) == "MATCH (n) RETURN n"

    def test_strips_cql_fence(self):
        raw = "```cql\nMATCH (n) RETURN n\n```"
        assert _clean_cypher(raw) == "MATCH (n) RETURN n"

    def test_plain_cypher_passed_through(self):
        raw = "MATCH (n:User) RETURN n LIMIT 10"
        assert _clean_cypher(raw) == raw

    def test_strips_leading_cypher_prefix(self):
        raw = "cypher\nMATCH (n) RETURN n"
        assert _clean_cypher(raw) == "MATCH (n) RETURN n"


# ── inject_limit ─────────────────────────────────────────────────────────


class TestInjectLimit:
    def test_adds_limit_when_missing(self):
        result = _inject_limit("MATCH (n) RETURN n", 25)
        assert result.endswith("LIMIT 25")

    def test_preserves_existing_limit(self):
        cypher = "MATCH (n) RETURN n LIMIT 10"
        result = _inject_limit(cypher, 25)
        assert "LIMIT 10" in result
        assert "LIMIT 25" not in result

    def test_case_insensitive_limit_detection(self):
        cypher = "MATCH (n) RETURN n limit 10"
        result = _inject_limit(cypher, 25)
        assert "LIMIT 25" not in result

    def test_strips_trailing_semicolon(self):
        result = _inject_limit("MATCH (n) RETURN n;", 25)
        assert result.endswith("LIMIT 25")
        assert ";" not in result


# ── detect_unknown_labels ────────────────────────────────────────────────


class TestDetectUnknownLabels:
    def test_no_unknowns(self):
        cypher = "MATCH (u:User)-[:PURCHASED]->(o:Order) RETURN u, o"
        result = _detect_unknown_labels(cypher, _sample_schema())
        assert result == []

    def test_detects_unknown_label(self):
        cypher = "MATCH (p:Product) RETURN p"
        result = _detect_unknown_labels(cypher, _sample_schema())
        assert "Product" in result

    def test_detects_unknown_relationship(self):
        cypher = "MATCH ()-[:FRIENDS_WITH]->() RETURN count(*)"
        result = _detect_unknown_labels(cypher, _sample_schema())
        assert "FRIENDS_WITH" in result

    def test_case_insensitive_matching(self):
        cypher = "MATCH (u:user) RETURN u"
        result = _detect_unknown_labels(cypher, _sample_schema())
        assert result == []


# ── CypherGenerator ──────────────────────────────────────────────────────


class TestCypherGenerator:
    @pytest.mark.asyncio
    async def test_successful_generation(self):
        client = _make_client("MATCH (u:User) RETURN u LIMIT 10")
        gen = CypherGenerator(client, model="llama3")
        result = await gen.generate("show all users", _sample_schema())

        assert isinstance(result, CypherGenerationResult)
        assert result.cypher == "MATCH (u:User) RETURN u LIMIT 10"
        assert result.question == "show all users"
        assert result.used_fallback is False
        assert result.error is None
        assert result.unknown_labels == []

    @pytest.mark.asyncio
    async def test_generation_strips_fences(self):
        client = _make_client("```cypher\nMATCH (u:User) RETURN u\n```")
        gen = CypherGenerator(client, model="llama3")
        result = await gen.generate("show users", _sample_schema())

        assert "```" not in result.cypher
        assert result.cypher.startswith("MATCH")

    @pytest.mark.asyncio
    async def test_generation_injects_limit(self):
        client = _make_client("MATCH (u:User) RETURN u")
        gen = CypherGenerator(client, model="llama3", default_limit=50)
        result = await gen.generate("show users", _sample_schema())

        assert "LIMIT 50" in result.cypher

    @pytest.mark.asyncio
    async def test_generation_detects_unknown_labels(self):
        client = _make_client("MATCH (p:Product) RETURN p LIMIT 10")
        gen = CypherGenerator(client, model="llama3")
        result = await gen.generate("show products", _sample_schema())

        assert "Product" in result.unknown_labels

    @pytest.mark.asyncio
    async def test_no_client_returns_fallback(self):
        gen = CypherGenerator(None, model=None)
        result = await gen.generate("show users", _sample_schema())

        assert result.used_fallback is True
        assert result.cypher == ""
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_empty_llm_response_returns_fallback(self):
        client = _make_client("")
        gen = CypherGenerator(client, model="llama3")
        result = await gen.generate("show users", _sample_schema())

        assert result.used_fallback is True
        assert result.cypher == ""

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self):
        import asyncio

        client = MagicMock()
        client.provider_name = "ollama"

        async def slow_generate(**kwargs):
            await asyncio.sleep(10)
            return "MATCH (n) RETURN n"

        client.generate = slow_generate
        gen = CypherGenerator(client, model="llama3", timeout_seconds=0.01)
        result = await gen.generate("show users", _sample_schema())

        assert result.used_fallback is True
        assert "timed out" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_exception_returns_fallback(self):
        client = MagicMock()
        client.provider_name = "ollama"
        client.generate = AsyncMock(side_effect=RuntimeError("LLM down"))
        gen = CypherGenerator(client, model="llama3")
        result = await gen.generate("show users", _sample_schema())

        assert result.used_fallback is True
        assert result.error is not None


# ── Factory ──────────────────────────────────────────────────────────────


class TestGetCypherGenerator:
    @pytest.mark.asyncio
    async def test_factory_returns_generator(self):
        with patch("src.llm.get_llm_client") as mock_get:
            mock_get.return_value = MagicMock()
            gen = await get_cypher_generator(db_session=None)
            assert isinstance(gen, CypherGenerator)

    @pytest.mark.asyncio
    async def test_factory_with_db_session(self):
        mock_router = MagicMock()
        mock_router.get_model_for_task.return_value = "gpt-4"
        mock_router.get_timeout_for_task.return_value = 30
        mock_router.get_provider_for_task.return_value = "openai"

        with patch("src.llm.get_llm_client") as mock_get:
            mock_get.return_value = MagicMock()
            with patch(
                "src.llm.model_router.get_model_router",
                new=AsyncMock(return_value=mock_router),
            ):
                gen = await get_cypher_generator(db_session=MagicMock())
                assert gen.model == "gpt-4"
                assert gen.timeout_seconds == 30.0
