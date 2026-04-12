"""Tests for Phase 12.5: Conversational Lineage

Tests the LineageConversationAgent for natural language Q&A about
lineage, schema, patterns, and recommendations.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.lineage.lineage_conversation_agent import (
    LineageConversationAgent,
    LineageAnswer,
    ConversationContext,
    QuestionClassifier,
    QuestionType,
    get_lineage_conversation_agent,
)


# =============================================================================
# LineageAnswer Tests
# =============================================================================

class TestLineageAnswer:
    """Tests for LineageAnswer dataclass."""

    def test_answer_to_dict(self):
        """Test serialization to dict."""
        answer = LineageAnswer(
            question="What tables are most used?",
            question_type="pattern",
            answer="The orders table is most used with 150 queries.",
            supporting_data={"total_queries": 150},
            related_tables=["orders", "customers"],
            related_queries=[1, 2, 3],
            confidence=0.85,
            follow_up_suggestions=["Show me slow queries"],
            llm_used=True,
        )

        result = answer.to_dict()

        assert result["question"] == "What tables are most used?"
        assert result["question_type"] == "pattern"
        assert result["confidence"] == 0.85
        assert result["llm_used"] is True
        assert "orders" in result["related_tables"]
        assert result["supporting_data"]["total_queries"] == 150

    def test_answer_post_init_timestamp(self):
        """Test that generated_at is auto-populated."""
        answer = LineageAnswer(
            question="test",
            question_type="general",
            answer="test answer",
        )

        assert answer.generated_at is not None
        # Should be a valid ISO timestamp
        datetime.fromisoformat(answer.generated_at)


# =============================================================================
# ConversationContext Tests
# =============================================================================

class TestConversationContext:
    """Tests for ConversationContext."""

    def test_add_turn(self):
        """Test adding conversation turns."""
        context = ConversationContext(
            session_id="test-session",
            connection_id=1,
        )

        context.add_turn("What tables exist?", "There are 5 tables.")
        context.add_turn("Show me orders", "The orders table has 10 columns.")

        assert len(context.history) == 2
        assert context.history[0] == ("What tables exist?", "There are 5 tables.")

    def test_add_turn_limits_history(self):
        """Test that history is limited to 5 turns."""
        context = ConversationContext(
            session_id="test-session",
            connection_id=1,
        )

        # Add 7 turns
        for i in range(7):
            context.add_turn(f"Question {i}", f"Answer {i}")

        # Should only keep last 5
        assert len(context.history) == 5
        assert context.history[0] == ("Question 2", "Answer 2")
        assert context.history[-1] == ("Question 6", "Answer 6")

    def test_get_context_summary(self):
        """Test context summary generation."""
        context = ConversationContext(
            session_id="test-session",
            connection_id=1,
            mentioned_tables=["orders", "customers"],
            mentioned_columns=["id", "name"],
        )
        context.add_turn("What is orders?", "It's a table.")

        summary = context.get_context_summary()

        assert "orders" in summary
        assert "customers" in summary
        assert "Recent conversation:" in summary

    def test_get_context_summary_empty(self):
        """Test context summary when empty."""
        context = ConversationContext(
            session_id="test-session",
            connection_id=1,
        )

        summary = context.get_context_summary()
        assert summary == ""


# =============================================================================
# QuestionClassifier Tests
# =============================================================================

class TestQuestionClassifier:
    """Tests for QuestionClassifier."""

    def test_classify_lineage_question(self):
        """Test classification of lineage questions."""
        classifier = QuestionClassifier()

        questions = [
            "What feeds into the orders table?",
            "Where does customer_id come from?",
            "Show me the data lineage for sales",
            "What are the upstream dependencies?",
        ]

        for q in questions:
            result = classifier.classify(q)
            assert result == QuestionType.LINEAGE, f"Failed for: {q}"

    def test_classify_impact_question(self):
        """Test classification of impact questions."""
        classifier = QuestionClassifier()

        questions = [
            "What breaks if I change the users table?",
            "What's the impact of dropping customer_id?",
            "What queries are affected by this change?",
            "What happens if I modify this column?",
        ]

        for q in questions:
            result = classifier.classify(q)
            assert result == QuestionType.IMPACT, f"Failed for: {q}"

    def test_classify_pattern_question(self):
        """Test classification of pattern questions."""
        classifier = QuestionClassifier()

        questions = [
            "What are the most used tables?",
            "Show me the query patterns",
            "What's causing the slow performance?",
            "What's the most frequent query?",
        ]

        for q in questions:
            result = classifier.classify(q)
            assert result == QuestionType.PATTERN, f"Failed for: {q}"

    def test_classify_schema_question(self):
        """Test classification of schema questions."""
        classifier = QuestionClassifier()

        questions = [
            "What columns does users have?",
            "Describe the orders table",
            "Show me the schema for customers",
            "What's the structure of this table?",
        ]

        for q in questions:
            result = classifier.classify(q)
            assert result == QuestionType.SCHEMA, f"Failed for: {q}"

    def test_classify_recommendation_question(self):
        """Test classification of recommendation questions."""
        classifier = QuestionClassifier()

        questions = [
            "How can I optimize my queries?",
            "What indexes should I add?",
            "Can you suggest improvements?",
            "What's the best practice here?",
        ]

        for q in questions:
            result = classifier.classify(q)
            assert result == QuestionType.RECOMMENDATION, f"Failed for: {q}"

    def test_classify_general_question(self):
        """Test classification of general questions."""
        classifier = QuestionClassifier()

        questions = [
            "Hello",
            "What can you do?",
            "Help me",
        ]

        for q in questions:
            result = classifier.classify(q)
            assert result == QuestionType.GENERAL, f"Failed for: {q}"

    def test_extract_entities_tables(self):
        """Test entity extraction for tables."""
        classifier = QuestionClassifier()

        entities = classifier.extract_entities("Show me data from customers table")
        assert "customers" in entities["tables"]

        entities = classifier.extract_entities("SELECT * FROM orders JOIN users")
        assert "orders" in entities["tables"]
        assert "users" in entities["tables"]

    def test_extract_entities_quoted(self):
        """Test entity extraction for quoted identifiers."""
        classifier = QuestionClassifier()

        entities = classifier.extract_entities("What is the 'orders' table?")
        assert "orders" in entities["tables"]

    def test_extract_entities_columns(self):
        """Test entity extraction for columns."""
        classifier = QuestionClassifier()

        entities = classifier.extract_entities("What is the customer_id column used for?")
        assert "customer_id" in entities["columns"]


# =============================================================================
# LineageConversationAgent Tests
# =============================================================================

class TestLineageConversationAgent:
    """Tests for LineageConversationAgent."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Ollama client."""
        client = MagicMock()
        client.generate = AsyncMock(return_value="This is a test answer from the LLM.")
        return client

    @pytest.fixture
    def agent(self, mock_client):
        """Create an agent with mocked client."""
        return LineageConversationAgent(
            client=mock_client,
            timeout_seconds=5.0,
        )

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        # Mock execute to return empty results by default
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result
        return db

    @pytest.mark.asyncio
    async def test_ask_classifies_question(self, agent, mock_db):
        """Test that questions are properly classified."""
        # Mock _get_queries_for_tables to return empty list
        agent._get_queries_for_tables = AsyncMock(return_value=[])
        agent._get_query_stats = AsyncMock(return_value={
            "total_queries": 0,
            "unique_queries": 0,
            "top_tables": [],
            "table_usage": {},
        })

        answer = await agent.ask(
            question="What are the most used tables?",
            connection_id=1,
            db=mock_db,
        )

        assert answer.question_type == "pattern"

    @pytest.mark.asyncio
    async def test_ask_pattern_question(self, agent, mock_db):
        """Test answering a pattern question."""
        agent._get_query_stats = AsyncMock(return_value={
            "total_queries": 100,
            "unique_queries": 50,
            "top_tables": ["orders", "customers", "products"],
            "table_usage": {"orders": 50, "customers": 30, "products": 20},
        })

        answer = await agent.ask(
            question="What are the most used tables?",
            connection_id=1,
            db=mock_db,
        )

        assert answer.question_type == "pattern"
        assert answer.llm_used is True
        assert len(answer.supporting_data) > 0

    @pytest.mark.asyncio
    async def test_ask_schema_question_no_tables(self, agent, mock_db):
        """Test schema question when no tables specified."""
        agent._get_schema_info = AsyncMock(return_value={"tables": {}})
        agent._get_all_tables = AsyncMock(return_value=["orders", "customers"])

        answer = await agent.ask(
            question="Show me the schema",
            connection_id=1,
            db=mock_db,
        )

        assert answer.question_type == "schema"
        assert "orders" in answer.answer or "tables" in answer.answer.lower()

    @pytest.mark.asyncio
    async def test_ask_with_session_id(self, agent, mock_db):
        """Test that session ID maintains conversation context."""
        agent._get_query_stats = AsyncMock(return_value={
            "total_queries": 10,
            "unique_queries": 5,
            "top_tables": ["orders"],
            "table_usage": {"orders": 10},
        })

        session_id = "test-session-123"

        # First question
        await agent.ask(
            question="What tables exist?",
            connection_id=1,
            db=mock_db,
            session_id=session_id,
        )

        # Second question with same session
        answer = await agent.ask(
            question="Tell me more about those",
            connection_id=1,
            db=mock_db,
            session_id=session_id,
        )

        # Context should be maintained
        context = agent._conversation_contexts.get(session_id)
        assert context is not None
        assert len(context.history) == 2

    @pytest.mark.asyncio
    async def test_ask_lineage_needs_table(self, agent, mock_db):
        """Test lineage question prompts for table when none specified."""
        answer = await agent.ask(
            question="What is the data lineage?",
            connection_id=1,
            db=mock_db,
        )

        assert answer.question_type == "lineage"
        assert "table" in answer.answer.lower() or "column" in answer.answer.lower()
        assert answer.confidence < 1.0

    @pytest.mark.asyncio
    async def test_format_dict(self, agent):
        """Test dict formatting for prompts."""
        data = {
            "name": "test",
            "count": 10,
            "items": ["a", "b", "c"],
            "nested": {"key": "value"},
        }

        result = agent._format_dict(data)

        assert "name: test" in result
        assert "count: 10" in result
        assert "items:" in result
        assert "nested:" in result


# =============================================================================
# LLM Integration Tests
# =============================================================================

class TestLineageConversationAgentLLM:
    """Tests for LLM integration in LineageConversationAgent."""

    @pytest.mark.asyncio
    async def test_llm_timeout_uses_fallback(self):
        """Test that LLM timeout falls back gracefully."""
        import asyncio

        client = MagicMock()
        client.generate = AsyncMock(side_effect=asyncio.TimeoutError())

        agent = LineageConversationAgent(client=client, timeout_seconds=0.1)

        result = await agent._call_llm("test prompt", "fallback answer")
        assert result == "fallback answer"

    @pytest.mark.asyncio
    async def test_llm_error_uses_fallback(self):
        """Test that LLM error falls back gracefully."""
        client = MagicMock()
        client.generate = AsyncMock(side_effect=Exception("LLM error"))

        agent = LineageConversationAgent(client=client, timeout_seconds=5.0)

        result = await agent._call_llm("test prompt", "fallback answer")
        assert result == "fallback answer"

    @pytest.mark.asyncio
    async def test_llm_empty_response_uses_fallback(self):
        """Test that empty LLM response falls back."""
        client = MagicMock()
        client.generate = AsyncMock(return_value="")

        agent = LineageConversationAgent(client=client, timeout_seconds=5.0)

        result = await agent._call_llm("test prompt", "fallback answer")
        assert result == "fallback answer"


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestGetLineageConversationAgent:
    """Tests for the factory function."""

    @pytest.mark.asyncio
    async def test_get_agent_without_db(self):
        """Test creating agent without database session."""
        with patch("src.lineage.lineage_conversation_agent.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            agent = await get_lineage_conversation_agent()

            assert agent is not None
            assert agent.client == mock_client
            assert agent.timeout_seconds == 15.0

    @pytest.mark.asyncio
    async def test_get_agent_with_model_override(self):
        """Test creating agent with model override."""
        with patch("src.lineage.lineage_conversation_agent.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            agent = await get_lineage_conversation_agent(model_override="llama3.2")

            mock_get_client.assert_called_once_with(None)
            assert agent is not None
            assert agent.model == "llama3.2"

    @pytest.mark.asyncio
    async def test_get_agent_with_timeout_override(self):
        """Test creating agent with timeout override."""
        with patch("src.lineage.lineage_conversation_agent.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            agent = await get_lineage_conversation_agent(timeout_override=30.0)

            assert agent.timeout_seconds == 30.0

    @pytest.mark.asyncio
    async def test_get_agent_with_db_uses_router(self):
        """Test creating agent with db session loads settings from model router."""
        with patch("src.lineage.lineage_conversation_agent.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            mock_db = MagicMock()
            mock_router = MagicMock()
            mock_router.get_model_for_task.return_value = "gemma3:4b"
            mock_router.get_timeout_for_task.return_value = 20.0

            # Patch the import location (src.llm.model_router.get_model_router)
            with patch("src.llm.model_router.get_model_router") as mock_get_router:
                # Make get_model_router an async function
                async def async_get_router(db):
                    return mock_router
                mock_get_router.side_effect = async_get_router

                agent = await get_lineage_conversation_agent(db=mock_db)

                assert agent.model == "gemma3:4b"
                assert agent.timeout_seconds == 20.0


# =============================================================================
# QuestionType Tests
# =============================================================================

class TestQuestionType:
    """Tests for QuestionType enum."""

    def test_question_type_values(self):
        """Test all question type values."""
        assert QuestionType.LINEAGE.value == "lineage"
        assert QuestionType.IMPACT.value == "impact"
        assert QuestionType.PATTERN.value == "pattern"
        assert QuestionType.SCHEMA.value == "schema"
        assert QuestionType.RECOMMENDATION.value == "recommendation"
        assert QuestionType.GENERAL.value == "general"

    def test_question_type_count(self):
        """Test number of question types."""
        assert len(QuestionType) == 6


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.generate = AsyncMock(return_value="Test response")
        return client

    @pytest.fixture
    def agent(self, mock_client):
        return LineageConversationAgent(
            client=mock_client,
            timeout_seconds=5.0,
        )

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result
        return db

    @pytest.mark.asyncio
    async def test_empty_question(self, agent, mock_db):
        """Test handling of edge case questions."""
        agent._get_database_info = AsyncMock(return_value={
            "connection_name": "test",
            "db_type": "postgresql",
            "table_count": 0,
            "tables": [],
            "total_queries": 0,
        })

        # Short/simple questions should still work
        answer = await agent.ask(
            question="Hi",
            connection_id=1,
            db=mock_db,
        )

        assert answer.question_type == "general"
        assert answer.answer is not None

    @pytest.mark.asyncio
    async def test_create_error_answer(self, agent):
        """Test error answer creation."""
        answer = agent._create_error_answer(
            question="test question",
            question_type=QuestionType.LINEAGE,
            error="Test error message",
        )

        assert answer.question == "test question"
        assert answer.question_type == "lineage"
        assert "error" in answer.answer.lower()
        assert answer.confidence == 0.0
        assert len(answer.follow_up_suggestions) > 0

    @pytest.mark.asyncio
    async def test_fallback_lineage_answer(self, agent):
        """Test fallback lineage answer generation."""
        tables = ["orders", "customers"]
        lineage_info = {
            "tables": {
                "orders": {"query_count": 10, "used_in_joins": 5, "sample_queries": []},
                "customers": {"query_count": 8, "used_in_joins": 3, "sample_queries": []},
            },
            "relationships": [{"from": "orders", "to": "customers", "type": "join"}],
        }

        result = agent._fallback_lineage_answer(tables, lineage_info)

        assert "orders" in result
        assert "customers" in result
        assert "10 queries" in result
        assert "Relationships" in result

    def test_generate_lineage_followups(self, agent):
        """Test follow-up suggestion generation."""
        followups = agent._generate_lineage_followups(["orders", "customers"])

        assert len(followups) <= 3
        assert any("orders" in f for f in followups)

    def test_generate_impact_followups(self, agent):
        """Test impact follow-up suggestion generation."""
        followups = agent._generate_impact_followups(["orders"], ["customer_id"])

        assert len(followups) <= 3
        assert any("migration" in f.lower() or "lineage" in f.lower() for f in followups)
