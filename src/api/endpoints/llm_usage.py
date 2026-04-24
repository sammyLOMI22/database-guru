from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

from src.api.dependencies import get_db
from src.auth.dependencies import require_admin
from src.database.models import LLMUsage
from src.models.schemas import (
    LLMUsageResponse,
    LLMUsageStatsResponse,
    LLMUsageByAgentResponse,
    LLMUsageByModelResponse,
    LLMUsageByProviderResponse,
    LLMUsageTimeSeriesResponse,
    SessionUsageSummaryResponse,
    ModelConfigResponse,
    ModelConfigCreateRequest,
    UnpricedModelResponse,
    CostSummaryResponse,
    ProviderComparisonResponse,
)

router = APIRouter(prefix="/llm/usage", tags=["LLM Usage"])

@router.get("/stats", response_model=LLMUsageStatsResponse)
async def get_usage_stats(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get overall LLM usage statistics for the past N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

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
    db: AsyncSession = Depends(get_db),
):
    """Get LLM usage breakdown by agent type."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

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

@router.get("/by-model", response_model=List[LLMUsageByModelResponse])
async def get_usage_by_model(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get LLM usage breakdown by model."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

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

@router.get("/by-provider", response_model=List[LLMUsageByProviderResponse])
async def get_usage_by_provider(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get LLM usage breakdown by provider."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            LLMUsage.provider,
            func.count(LLMUsage.id).label("total_calls"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.avg(LLMUsage.response_time_ms).label("avg_response_time_ms"),
            func.sum(LLMUsage.estimated_cost_usd).label("total_cost"),
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
            "total_cost_usd": row.total_cost or 0.0,
        }
        for row in result.all()
    ]

@router.get("/timeseries", response_model=List[LLMUsageTimeSeriesResponse])
async def get_usage_timeseries(
    days: int = Query(default=7, ge=1, le=90),
    granularity: str = Query(default="hour", enum=["hour", "day"]),
    db: AsyncSession = Depends(get_db),
):
    """Get LLM usage over time for charting."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger usage aggregation."""
    from src.services.llm_usage_aggregator import LLMUsageAggregator
    await LLMUsageAggregator.aggregate_usage(db, days_back=days)
    return {"message": f"Successfully aggregated usage for the last {days} days"}

@router.post("/configs/seed")
async def seed_model_configs(
    db: AsyncSession = Depends(get_db),
):
    """Seed default model configurations (no-op, pricing is user-managed)."""
    return {"message": "Model pricing is user-managed. Use POST /llm/usage/model-configs to configure."}


# ============================================================================
# Model Pricing Admin Endpoints (Phase 17)
# ============================================================================

@router.get("/model-configs", response_model=List[ModelConfigResponse])
async def list_model_configs(
    db: AsyncSession = Depends(get_db),
):
    """List all model pricing configurations."""
    from src.services.llm_cost_service import LLMCostService
    configs = await LLMCostService.get_all_configs(db)
    return configs


@router.get("/unpriced-models", response_model=List[UnpricedModelResponse])
async def list_unpriced_models(
    db: AsyncSession = Depends(get_db),
):
    """List models seen in usage records that have no pricing configured."""
    from src.services.llm_cost_service import LLMCostService
    return await LLMCostService.get_unpriced_models(db)


@router.post("/model-configs", response_model=ModelConfigResponse)
async def upsert_model_config(
    request: ModelConfigCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Create or update a model pricing configuration. Admin only."""
    from src.services.llm_cost_service import LLMCostService
    config = await LLMCostService.upsert_model_config(
        db,
        model_name=request.model_name,
        provider=request.provider,
        cost_per_1m_input_tokens=request.cost_per_1m_input_tokens,
        cost_per_1m_output_tokens=request.cost_per_1m_output_tokens,
        display_name=request.display_name,
    )
    return config


@router.delete("/model-configs/{provider}/{model_name:path}")
async def delete_model_config(
    provider: str,
    model_name: str,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Delete a model pricing configuration. Admin only."""
    from src.services.llm_cost_service import LLMCostService
    deleted = await LLMCostService.delete_model_config(db, model_name, provider)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Model config '{provider}/{model_name}' not found",
        )
    return {"message": f"Model config '{provider}/{model_name}' deleted"}


# ============================================================================
# Cost Summary & Provider Comparison Endpoints (Phase 17)
# ============================================================================

@router.get("/cost-summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get cost summary across all providers with daily breakdown."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Overall totals
    result = await db.execute(
        select(
            func.sum(LLMUsage.estimated_cost_usd).label("total_cost"),
            func.sum(LLMUsage.input_tokens).label("total_input_tokens"),
            func.sum(LLMUsage.output_tokens).label("total_output_tokens"),
            func.count(LLMUsage.id).label("total_calls"),
        )
        .where(LLMUsage.created_at >= since)
    )
    row = result.one()
    total_cost = row.total_cost or 0.0
    total_calls = row.total_calls or 0

    # Daily breakdown
    daily_result = await db.execute(
        select(
            func.date(LLMUsage.created_at).label("date"),
            func.sum(LLMUsage.estimated_cost_usd).label("cost"),
            func.count(LLMUsage.id).label("calls"),
            func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).label("tokens"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(func.date(LLMUsage.created_at))
        .order_by(func.date(LLMUsage.created_at))
    )

    # By provider subtotals
    provider_result = await db.execute(
        select(
            LLMUsage.provider,
            func.sum(LLMUsage.estimated_cost_usd).label("cost"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(LLMUsage.provider)
    )

    return {
        "period_days": days,
        "total_cost_usd": total_cost,
        "total_tokens": (row.total_input_tokens or 0) + (row.total_output_tokens or 0),
        "total_calls": total_calls,
        "avg_cost_per_call": total_cost / total_calls if total_calls > 0 else 0.0,
        "daily_costs": [
            {
                "date": str(r.date),
                "cost_usd": r.cost or 0.0,
                "calls": r.calls or 0,
                "tokens": r.tokens or 0,
            }
            for r in daily_result.all()
        ],
        "by_provider": {
            r.provider: r.cost or 0.0
            for r in provider_result.all()
        },
    }


@router.get("/provider-comparison", response_model=ProviderComparisonResponse)
async def get_provider_comparison(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Compare performance and cost across providers, grouped by agent type."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            LLMUsage.provider,
            LLMUsage.agent_type,
            func.count(LLMUsage.id).label("calls"),
            func.avg(LLMUsage.response_time_ms).label("avg_latency"),
            func.sum(LLMUsage.estimated_cost_usd).label("total_cost"),
            func.avg(LLMUsage.input_tokens + LLMUsage.output_tokens).label("avg_tokens"),
            func.sum(case((LLMUsage.success == True, 1), else_=0)).label("success_count"),
        )
        .where(LLMUsage.created_at >= since)
        .group_by(LLMUsage.provider, LLMUsage.agent_type)
    )

    by_agent_type: Dict[str, Dict] = {}
    for row in result.all():
        agent = row.agent_type
        if agent not in by_agent_type:
            by_agent_type[agent] = {}
        by_agent_type[agent][row.provider] = {
            "calls": row.calls,
            "avg_latency_ms": row.avg_latency,
            "total_cost_usd": row.total_cost or 0.0,
            "avg_tokens_per_call": row.avg_tokens,
            "success_rate": (row.success_count / row.calls * 100) if row.calls > 0 else 0.0,
        }

    return {"period_days": days, "by_agent_type": by_agent_type}
