"""Tests for Conversational Memory Agent"""
import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, ChatSession, ChatMessage, QueryHistory
from src.llm.conversational_memory_agent import (
    ConversationalMemoryAgent,
    ConversationContext,
    get_memory_agent
)


@pytest.fixture
async def db_session():
    """Create an in-memory test database"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_session(db_session: AsyncSession):
    """Create a test chat session"""
    session = ChatSession(
        name="Test Session",
        user_id="test_user",
        active_connection_ids=[1]
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture
async def test_queries(db_session: AsyncSession):
    """Create test query history records"""
    queries = [
        QueryHistory(
            natural_language_query="Show me all products",
            generated_sql="SELECT * FROM products",
            sql_validated=True,
            executed=True,
            result_count=100,
            database_type="postgresql",
            model_used="qwen2.5-coder:32b"
        ),
        QueryHistory(
            natural_language_query="Filter by electronics",
            generated_sql="SELECT * FROM products WHERE category = 'electronics'",
            sql_validated=True,
            executed=True,
            result_count=25,
            database_type="postgresql",
            model_used="qwen2.5-coder:32b"
        ),
        QueryHistory(
            natural_language_query="Sort by price",
            generated_sql="SELECT * FROM products WHERE category = 'electronics' ORDER BY price",
            sql_validated=True,
            executed=True,
            result_count=25,
            database_type="postgresql",
            model_used="qwen2.5-coder:32b"
        )
    ]

    for q in queries:
        db_session.add(q)

    await db_session.commit()

    for q in queries:
        await db_session.refresh(q)

    return queries


@pytest.fixture
async def test_messages(db_session: AsyncSession, test_session: ChatSession, test_queries):
    """Create test chat messages linked to queries"""
    messages = []

    for i, query in enumerate(test_queries):
        # User message
        user_msg = ChatMessage(
            chat_session_id=test_session.id,
            role="user",
            content=query.natural_language_query,
            query_history_id=query.id
        )
        db_session.add(user_msg)
        messages.append(user_msg)

        # Assistant message
        assistant_msg = ChatMessage(
            chat_session_id=test_session.id,
            role="assistant",
            content=f"```sql\n{query.generated_sql}\n```\n\nReturned {query.result_count} rows",
            query_history_id=query.id
        )
        db_session.add(assistant_msg)
        messages.append(assistant_msg)

    await db_session.commit()

    for msg in messages:
        await db_session.refresh(msg)

    return messages


@pytest.mark.asyncio
class TestConversationalMemoryAgent:
    """Test suite for ConversationalMemoryAgent"""

    async def test_initialization(self):
        """Test agent initialization"""
        agent = ConversationalMemoryAgent(context_window=5)
        assert agent.context_window == 5

    async def test_get_context_empty_session(self, db_session, test_session):
        """Test getting context from session with no messages"""
        agent = ConversationalMemoryAgent()
        context = await agent.get_context(test_session.id, db_session)

        assert isinstance(context, ConversationContext)
        assert context.has_context is False
        assert context.context_window_size == 0
        assert len(context.messages) == 0

    async def test_get_context_with_messages(self, db_session, test_session, test_messages):
        """Test getting context from session with messages"""
        agent = ConversationalMemoryAgent(context_window=3)
        context = await agent.get_context(test_session.id, db_session)

        assert context.has_context is True
        assert context.context_window_size == 3  # Limited by context_window
        assert len(context.messages) == 3

        # Check message structure
        for msg in context.messages:
            assert "question" in msg
            assert "sql" in msg
            assert "executed" in msg
            assert "success" in msg

    async def test_context_window_limit(self, db_session, test_session, test_messages):
        """Test that context window limits messages correctly"""
        # Create agent with window size of 2
        agent = ConversationalMemoryAgent(context_window=2)
        context = await agent.get_context(test_session.id, db_session)

        # Should only get 2 most recent queries
        assert context.context_window_size == 2
        assert len(context.messages) == 2

        # Should be the most recent queries
        assert "electronics" in context.messages[0]["question"].lower()
        assert "price" in context.messages[1]["question"].lower()

    async def test_build_context_prompt_no_context(self):
        """Test building prompt when no context available"""
        agent = ConversationalMemoryAgent()
        context = ConversationContext(
            messages=[],
            has_context=False,
            context_window_size=0
        )

        question = "Show me all products"
        enhanced = agent.build_context_prompt(question, context)

        # Should return question as-is
        assert enhanced == question

    async def test_build_context_prompt_with_context(self):
        """Test building prompt with conversation context"""
        agent = ConversationalMemoryAgent()
        context = ConversationContext(
            messages=[
                {
                    "question": "Show me all products",
                    "sql": "SELECT * FROM products",
                    "executed": True,
                    "success": True,
                    "result_count": 100
                },
                {
                    "question": "Filter by electronics",
                    "sql": "SELECT * FROM products WHERE category = 'electronics'",
                    "executed": True,
                    "success": True,
                    "result_count": 25
                }
            ],
            has_context=True,
            context_window_size=2
        )

        question = "Sort by price"
        enhanced = agent.build_context_prompt(question, context)

        # Should include context with new secure XML-like format
        assert "<conversation_history>" in enhanced
        assert "<current_query>" in enhanced
        assert "Show me all products" in enhanced
        assert "Filter by electronics" in enhanced
        assert "Sort by price" in enhanced
        assert "previous query" in enhanced.lower() or "conversation history" in enhanced.lower()

    async def test_should_use_context(self):
        """Test context detection logic"""
        agent = ConversationalMemoryAgent()

        # Should use context - strong indicators (pronouns, directives)
        assert agent.should_use_context("filter that") is True
        assert agent.should_use_context("sort it") is True
        assert agent.should_use_context("also show") is True
        assert agent.should_use_context("add price") is True
        assert agent.should_use_context("those results") is True
        assert agent.should_use_context("the previous query") is True

        # Should use context - modification keywords at START
        assert agent.should_use_context("filter by price") is True
        assert agent.should_use_context("Filter by category") is True
        assert agent.should_use_context("sort by name") is True
        assert agent.should_use_context("order by date") is True
        assert agent.should_use_context("add where clause") is True

        # Short questions likely refinements
        assert agent.should_use_context("by category") is True

        # Standalone questions - complete queries with modification words in middle
        assert agent.should_use_context("Show me all customers from California") is False
        assert agent.should_use_context("Show all filtered results") is False
        assert agent.should_use_context("Get all sorted data") is False
        assert agent.should_use_context("Display products ordered by price") is False

        # Standalone questions - complete queries starting with modification keywords
        # Note: These will return True with current logic, which is a known limitation
        # but better than catching false positives in the middle of sentences
        assert agent.should_use_context("Filter all products by category") is True
        assert agent.should_use_context("Sort all customers by name") is True

    async def test_format_context_for_display(self):
        """Test formatting context for UI display"""
        agent = ConversationalMemoryAgent()
        context = ConversationContext(
            messages=[
                {
                    "question": "Show me all products",
                    "sql": "SELECT * FROM products",
                    "success": True,
                    "timestamp": "2025-01-01T00:00:00"
                }
            ],
            has_context=True,
            context_window_size=1
        )

        formatted = agent.format_context_for_display(context)

        assert formatted["has_context"] is True
        assert formatted["window_size"] == 1
        assert len(formatted["messages"]) == 1
        assert formatted["messages"][0]["question"] == "Show me all products"
        assert formatted["messages"][0]["sql"] == "SELECT * FROM products"

    async def test_get_memory_agent_singleton(self):
        """Test singleton pattern for memory agent"""
        agent1 = get_memory_agent()
        agent2 = get_memory_agent()

        # Should return same instance
        assert agent1 is agent2

    async def test_clear_context(self, db_session, test_session):
        """Test clearing context"""
        agent = ConversationalMemoryAgent()
        result = await agent.clear_context(test_session.id, db_session)

        assert result is True

    async def test_messages_ordered_oldest_first(self, db_session, test_session, test_messages):
        """Test that messages are returned in correct order (oldest first)"""
        agent = ConversationalMemoryAgent(context_window=3)
        context = await agent.get_context(test_session.id, db_session)

        # First message should be oldest
        assert "all products" in context.messages[0]["question"].lower()
        # Last message should be newest
        assert "price" in context.messages[-1]["question"].lower()

    async def test_context_with_failed_query(self, db_session, test_session):
        """Test context includes failed queries"""
        # Create a failed query
        failed_query = QueryHistory(
            natural_language_query="Show invalid table",
            generated_sql="SELECT * FROM invalid_table",
            sql_validated=True,
            executed=True,
            error_message="Table 'invalid_table' does not exist",
            database_type="postgresql",
            model_used="qwen2.5-coder:32b"
        )
        db_session.add(failed_query)
        await db_session.commit()
        await db_session.refresh(failed_query)

        # Create message linked to failed query
        user_msg = ChatMessage(
            chat_session_id=test_session.id,
            role="user",
            content=failed_query.natural_language_query,
            query_history_id=failed_query.id
        )
        db_session.add(user_msg)
        await db_session.commit()

        agent = ConversationalMemoryAgent()
        context = await agent.get_context(test_session.id, db_session)

        assert context.has_context is True
        assert len(context.messages) == 1
        # Failed query should be marked as not successful
        assert context.messages[0]["success"] is False

    async def test_context_only_includes_user_messages(self, db_session, test_session, test_queries):
        """Test that context only tracks user questions, not assistant responses"""
        agent = ConversationalMemoryAgent(context_window=5)

        # Create user messages only
        for query in test_queries:
            user_msg = ChatMessage(
                chat_session_id=test_session.id,
                role="user",
                content=query.natural_language_query,
                query_history_id=query.id
            )
            db_session.add(user_msg)

        # Add some system messages (should be ignored)
        system_msg = ChatMessage(
            chat_session_id=test_session.id,
            role="system",
            content="System initialized"
        )
        db_session.add(system_msg)

        await db_session.commit()

        context = await agent.get_context(test_session.id, db_session)

        # Should only count user messages
        assert context.context_window_size == 3
        assert all("question" in msg for msg in context.messages)

    async def test_error_handling_invalid_session(self, db_session):
        """Test error handling for invalid session"""
        agent = ConversationalMemoryAgent()
        context = await agent.get_context("invalid-session-id", db_session)

        # Should return empty context on error
        assert context.has_context is False
        assert context.context_window_size == 0


@pytest.mark.asyncio
class TestConversationContextIntegration:
    """Integration tests for conversation context in query processing"""

    async def test_context_improves_query_generation(self):
        """Test that context improves follow-up query generation"""
        agent = ConversationalMemoryAgent()

        # Simulate previous context
        context = ConversationContext(
            messages=[
                {
                    "question": "Show me all products",
                    "sql": "SELECT * FROM products",
                    "executed": True,
                    "success": True,
                    "result_count": 100
                }
            ],
            has_context=True,
            context_window_size=1
        )

        # Follow-up question
        question = "filter by category electronics"
        enhanced = agent.build_context_prompt(question, context)

        # Enhanced prompt should include context
        assert "Show me all products" in enhanced
        assert "SELECT * FROM products" in enhanced
        assert "filter by category electronics" in enhanced
        assert "previous" in enhanced.lower() or "context" in enhanced.lower()
