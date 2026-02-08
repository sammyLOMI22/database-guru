from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from typing import Optional, List

from src.database.connection import get_db_manager
from src.database.models import LLMUsage
from src.models.schemas import (
    LLMUsageResponse,
    LLMUsageStatsResponse,
    LLMUsageByAgentResponse,
    LLMUsageTimeSeriesResponse,
    SessionUsageSummaryResponse,
)

router = APIRouter(prefix="/llm/usage", tags=["LLM Usage"])

async def get_session():
    """Dependency to get database session"""
    db_manager = get_db_manager()
    async with db_manager.get_async_session() as session:
        yield session

@router.get("/stats", response_model=LLMUsageStatsResponse)
async def get_usage_stats(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
):
    """Get overall LLM usage statistics for the past N days."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
            func.count(func.distinct(LLMUsage.chat_session_id)).label("unique_sessions"),
            func.count(func.distinct(LLMUsage.model_name)).label("models_used"),
            func.sum(LLMUsage.estimated_cost_usd).label("total_cost_usd"),
        ).where(LLMUsage.created_at >= since)
    )

    row = result.one()
    total_input = row.total_input_tokens or 0
    total_output = row.total_output_tokens or 0

    return {
        "period_days": days,
        "total_calls": row.total_calls or 0,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "avg_response_time_ms": row.avg_response_time_ms,
        "unique_sessions": row.unique_sessions or 0,
        "models_used": row.models_used or 0,
        "total_cost_usd": row.total_cost_usd or 0.0,
    }

@router.get("/by-agent", response_model=List[LLMUsageByAgentResponse])
async def get_usage_by_agent(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage breakdown by agent type."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            LLMUsage.agent_type,
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(LLMUsage.agent_type)
        .order_by(func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).desc())
    )

    return [
        {
            "agent_type": row.agent_type,
            "total_calls": row.total_calls,
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
            "avg_response_time_ms": row.avg_response_time_ms,
        }
        for row in result.all()
    ]

@router.get("/by-model", response_model=List[dict])
async def get_usage_by_model(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage breakdown by model."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            LLMUsage.model_name,
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(LLMUsage.model_name)
        .order_by(func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).desc())
    )

    return [
        {
            "model_name": row.model_name,
            "total_calls": row.total_calls,
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
            "avg_response_time_ms": row.avg_response_time_ms,
        }
        for row in result.all()
    ]

@router.get("/by-provider", response_model=List[dict])
async def get_usage_by_provider(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage breakdown by provider."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            LLMUsage.provider,
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(LLMUsage.provider)
        .order_by(func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).desc())
    )

    return [
        {
            "provider": row.provider,
            "total_calls": row.total_calls,
            "total_input_tokens": row.total_input_tokens or 0,
            "total_output_tokens": row.total_output_tokens or 0,
            "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
            "avg_response_time_ms": row.avg_response_time_ms,
        }
        for row in result.all()
    ]

@router.get("/timeseries", response_model=List[LLMUsageTimeSeriesResponse])
async def get_usage_timeseries(
    days: int = Query(default=7, ge=1, le=30),
    granularity: str = Query(default="hour", enum=["hour", "day"]),
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage over time for charting."""
    since = datetime.utcnow() - timedelta(days=days)

    if granularity == "day":
        result = await db.execute(
            select(
                func.date(LLMUsage.created_at).label("period"),
                func.count(LLMUsage.id).label("total_calls"),
                func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
                func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            )
            .where(LLMUsage.created_at >= since)
            .group_by(func.date(LLMUsage.created_at))
            .order_by(func.date(LLMUsage.created_at))
        )
    else:
        # SQLite specific strftime
        result = await db.execute(
            select(
                func.strftime('%Y-%m-%d %H:00', LLMUsage.created_at).label("period"),
                func.count(LLMUsage.id).label("total_calls"),
                func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
                func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            )
            .where(LLMUsage.created_at >= since)
            .group_by(func.strftime('%Y-%m-%d %H:00', LLMUsage.created_at))
            .order_by(func.strftime('%Y-%m-%d %H:00', LLMUsage.created_at))
        )

    return [
        {
            "period": str(row.period),
            "total_calls": row.total_calls,
            "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
        }
        for row in result.all()
    ]

@router.get("/session/{session_id}", response_model=SessionUsageSummaryResponse)
async def get_session_usage(
    session_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get LLM usage for a specific chat session."""
    result = await db.execute(
        select(
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
            func.min(LLMUsage.created_at).label("first_call"),
            func.max(LLMUsage.created_at).label("last_call"),
            func.sum(LLMUsage.estimated_cost_usd).label("total_cost_usd"),
        ).where(LLMUsage.chat_session_id == session_id)
    )

    row = result.one()
    if row.total_calls == 0:
        return {
            "session_id": session_id,
            "total_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "avg_response_time_ms": None,
            "first_call": None,
            "last_call": None,
            "total_cost_usd": 0.0,
            "by_agent": {},
        }

    # Get breakdown by agent
    agent_result = await db.execute(
        select(
            LLMUsage.agent_type,
            func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).label("tokens"),
        )
        .where(LLMUsage.chat_session_id == session_id)
        .group_by(LLMUsage.agent_type)
    )

    return {
        "session_id": session_id,
        "total_calls": row.total_calls or 0,
        "total_input_tokens": row.total_input_tokens or 0,
        "total_output_tokens": row.total_output_tokens or 0,
        "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
        "avg_response_time_ms": row.avg_response_time_ms,
        "first_call": row.first_call.isoformat() if row.first_call else None,
        "last_call": row.last_call.isoformat() if row.last_call else None,
        "total_cost_usd": row.total_cost_usd or 0.0,
        "by_agent": {r.agent_type: r.tokens for r in agent_result.all()},
    }

@router.get("/recent", response_model=List[LLMUsageResponse])
async def get_recent_usage(
    limit: int = Query(default=50, ge=1, le=500),
    agent_type: Optional[str] = None,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
):
    """Get recent LLM usage records for debugging/monitoring."""
    query = select(LLMUsage).order_by(LLMUsage.created_at.desc()).limit(limit)

    if agent_type:
        query = query.where(LLMUsage.agent_type == agent_type)
    if model_name:
        query = query.where(LLMUsage.model_name == model_name)
    if provider:
        query = query.where(LLMUsage.provider == provider)

    result = await db.execute(query)
    return result.scalars().all()

@router.post("/aggregate")
async def trigger_aggregation(
    days: int = Query(default=1, ge=0, le=30),
    db: AsyncSession = Depends(get_session),
):
    """Manually trigger usage aggregation."""
    from src.services.llm_usage_aggregator import LLMUsageAggregator
    await LLMUsageAggregator.aggregate_usage(db, days_back=days)
    return {"message": f"Successfully aggregated usage for the last {days} days"}

@router.post("/configs/seed")
async def seed_model_configs(
    db: AsyncSession = Depends(get_session),
):
    """Seed default model configurations."""
    from src.services.llm_cost_service import LLMCostService
    await LLMCostService.ensure_default_configs(db)
    return {"message": "Default model configurations seeded"}
