"""Service for aggregating LLM usage data into daily/hourly statistics"""
import logging
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, and_, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import LLMUsage, LLMUsageAggregate

logger = logging.getLogger(__name__)

class LLMUsageAggregator:
    """Service for aggregating LLM usage data into daily/hourly statistics."""

    @staticmethod
    async def aggregate_usage(db: AsyncSession, days_back: int = 1):
        """
        Aggregate usage for the last N days.
        Typically run as a background task.
        """
        today = date.today()
        for i in range(days_back + 1):
            target_date = today - timedelta(days=i)
            await LLMUsageAggregator.aggregate_date(db, target_date)

        await db.commit()

    @staticmethod
    async def aggregate_date(db: AsyncSession, target_date: date):
        """Aggregate all usage for a specific date, broken down by hour and agent."""
        logger.info(f"Aggregating LLM usage for {target_date}")

        # Breakdown by hour, agent_type, provider, model_name
        # Note: SQLite specific hour extraction if needed, but here we use a general approach

        # 1. Fetch raw totals for the day
        stmt = (
            select(
                func.strftime('%H', LLMUsage.created_at).label('hour'),
                LLMUsage.agent_type,
                LLMUsage.provider,
                LLMUsage.model_name,
                func.count(LLMUsage.id).label('total_calls'),
                func.sum(LLMUsage.success.cast(Integer)).label('successful_calls'),
                func.sum(LLMUsage.input_tokens).label('total_input_tokens'),
                func.sum(LLMUsage.output_tokens).label('total_output_tokens'),
                func.avg(LLMUsage.response_time_ms).label('avg_response_time'),
                func.max(LLMUsage.response_time_ms).label('max_response_time'),
                func.min(LLMUsage.response_time_ms).label('min_response_time'),
                func.sum(LLMUsage.estimated_cost_usd).label('total_cost'),
            )
            .where(func.date(LLMUsage.created_at) == target_date.isoformat())
            .group_by('hour', LLMUsage.agent_type, LLMUsage.provider, LLMUsage.model_name)
        )

        result = await db.execute(stmt)
        rows = result.all()

        for row in rows:
            hour = int(row.hour)

            # Upsert into LLMUsageAggregate
            agg_stmt = select(LLMUsageAggregate).where(
                and_(
                    LLMUsageAggregate.date == target_date,
                    LLMUsageAggregate.hour == hour,
                    LLMUsageAggregate.agent_type == row.agent_type,
                    LLMUsageAggregate.provider == row.provider,
                    LLMUsageAggregate.model_name == row.model_name
                )
            )

            agg_result = await db.execute(agg_stmt)
            agg = agg_result.scalar_one_or_none()

            if not agg:
                agg = LLMUsageAggregate(
                    date=target_date,
                    hour=hour,
                    agent_type=row.agent_type,
                    provider=row.provider,
                    model_name=row.model_name
                )
                db.add(agg)

            agg.total_calls = row.total_calls
            agg.successful_calls = row.successful_calls or 0
            agg.failed_calls = row.total_calls - (row.successful_calls or 0)
            agg.total_input_tokens = row.total_input_tokens or 0
            agg.total_output_tokens = row.total_output_tokens or 0
            agg.total_tokens = agg.total_input_tokens + agg.total_output_tokens
            agg.avg_response_time_ms = row.avg_response_time
            agg.max_response_time_ms = row.max_response_time
            agg.min_response_time_ms = row.min_response_time
            agg.total_estimated_cost_usd = row.total_cost or 0.0

        logger.info(f"Finished aggregation for {target_date}: {len(rows)} buckets updated")
