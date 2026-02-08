import pytest
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.database.models import Base, LLMUsage, LLMUsageAggregate, LLMModelConfig
from src.services.llm_cost_service import LLMCostService
from src.services.llm_usage_aggregator import LLMUsageAggregator
from src.services.llm_usage_tracker import LLMUsageTracker

@pytest.fixture
async def db_session():
    """Create a test async database session"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_llm_cost_calculation(db_session):
    # Seed configs
    await LLMCostService.ensure_default_configs(db_session)

    # Test local model (llama3) -> $0
    cost = await LLMCostService.calculate_cost(db_session, "llama3", 1000, 500)
    assert cost == 0.0

    # Test GPT-4o -> (1000/1M * 5) + (500/1M * 15) = 0.005 + 0.0075 = 0.0125
    cost = await LLMCostService.calculate_cost(db_session, "gpt-4o", 1000, 500)
    assert cost == 0.0125

@pytest.mark.asyncio
async def test_llm_usage_aggregation(db_session):
    # 1. Create some usage records
    today = date.today()
    usage1 = LLMUsage(
        agent_type="test_agent",
        model_name="gpt-4o",
        provider="openai",
        llm_method="chat",
        input_tokens=1000,
        output_tokens=500,
        estimated_cost_usd=0.0125,
        success=True,
        response_time_ms=100.0
    )
    usage2 = LLMUsage(
        agent_type="test_agent",
        model_name="gpt-4o",
        provider="openai",
        llm_method="chat",
        input_tokens=2000,
        output_tokens=1000,
        estimated_cost_usd=0.025,
        success=True,
        response_time_ms=200.0
    )
    db_session.add_all([usage1, usage2])
    await db_session.commit()

    # 2. Run aggregation
    await LLMUsageAggregator.aggregate_usage(db_session, days_back=0)

    # 3. Verify aggregate
    stmt = select(LLMUsageAggregate).where(LLMUsageAggregate.date == today)
    result = await db_session.execute(stmt)
    aggregates = result.scalars().all()

    assert len(aggregates) > 0
    agg = aggregates[0]
    assert agg.total_calls == 2
    assert agg.total_tokens == 4500
    assert agg.total_input_tokens == 3000
    assert agg.total_output_tokens == 1500
    assert agg.total_estimated_cost_usd == pytest.approx(0.0375)
    assert agg.avg_response_time_ms == 150.0

@pytest.mark.asyncio
async def test_token_estimation():
    tracker = LLMUsageTracker()
    text = "Hello, how are you today?"

    # Should use tiktoken if available
    tokens, method = tracker.estimate_tokens(text)
    assert tokens > 0
    assert method in ["tiktoken", "estimated"]

    # Empty text
    tokens, method = tracker.estimate_tokens("")
    assert tokens == 0
    assert method == "empty"
