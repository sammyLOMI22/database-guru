import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, LLMUsage, QueryHistory
from src.llm.sql_generator import SQLGenerator
from src.llm.ollama_client import OllamaClient
from src.config.settings import Settings

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_full_tracking_flow(db_session):
    # Mock OllamaClient
    settings = Settings()
    client = OllamaClient(settings)
    client.client = AsyncMock()

    # Mock successful response with tokens for chat
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "SELECT * FROM users;"},
        "prompt_eval_count": 15,
        "eval_count": 10
    }
    client.client.post = AsyncMock(return_value=mock_response)

    generator = SQLGenerator(settings, client)

    # Create a history record
    history = QueryHistory(
        natural_language_query="Show all users",
        generated_sql="PENDING",
    )
    db_session.add(history)
    await db_session.commit()
    await db_session.refresh(history)

    # Call generate_sql with tracking
    # Note: SQLGenerator.generate_sql calls OllamaClient.chat (via build_chat_messages)
    result = await generator.generate_sql(
        question="Show all users",
        schema="Table users(id, name)",
        db=db_session,
        query_history_id=history.id,
        chat_session_id="test_session"
    )

    assert "SELECT * FROM users" in result["sql"]

    # Verify usage was recorded in DB
    from sqlalchemy import select
    stmt = select(LLMUsage).where(LLMUsage.query_history_id == history.id)
    usage_result = await db_session.execute(stmt)
    usage = usage_result.scalar_one()

    assert usage.agent_type == "sql_generator"
    assert usage.input_tokens == 15
    assert usage.output_tokens == 10
    assert usage.chat_session_id == "test_session"
    assert usage.provider == "ollama"
    assert usage.token_estimation_method == "ollama_native"
