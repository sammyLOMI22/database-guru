"""Service for managing LLM model configurations and costs"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import LLMModelConfig, LLMUsage

logger = logging.getLogger(__name__)

class LLMCostService:
    """Service for managing LLM model configurations and costs."""

    @staticmethod
    async def get_model_config(db: AsyncSession, model_name: str) -> Optional[LLMModelConfig]:
        """Fetch configuration for a specific model."""
        # Try exact match first
        stmt = select(LLMModelConfig).where(LLMModelConfig.model_name == model_name)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            # Try fuzzy match (e.g. "llama3:latest" -> "llama3")
            # Order by name length to prefer exact prefix matches over longer ones
            base_name = model_name.split(":")[0]
            stmt = (
                select(LLMModelConfig)
                .where(LLMModelConfig.model_name.like(f"{base_name}%"))
                .order_by(func.length(LLMModelConfig.model_name))
            )
            result = await db.execute(stmt)
            config = result.scalars().first()

        return config

    @staticmethod
    async def calculate_cost(
        db: AsyncSession,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate the estimated cost in USD for a given model and token counts."""
        config = await LLMCostService.get_model_config(db, model_name)

        if not config or (config.cost_per_1m_input_tokens is None and config.cost_per_1m_output_tokens is None):
            # Default for Ollama/local models is $0.0
            return 0.0

        input_cost = (input_tokens / 1_000_000) * (config.cost_per_1m_input_tokens or 0)
        output_cost = (output_tokens / 1_000_000) * (config.cost_per_1m_output_tokens or 0)

        return input_cost + output_cost

    @staticmethod
    async def get_all_configs(db: AsyncSession) -> List[LLMModelConfig]:
        """List all model pricing configurations."""
        result = await db.execute(
            select(LLMModelConfig).order_by(LLMModelConfig.provider, LLMModelConfig.model_name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_unpriced_models(db: AsyncSession) -> List[Dict[str, Any]]:
        """Find models seen in usage records that have no pricing config."""
        configured = select(LLMModelConfig.model_name)
        result = await db.execute(
            select(
                LLMUsage.model_name,
                LLMUsage.provider,
                func.count(LLMUsage.id).label("call_count"),
                func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).label("total_tokens"),
            )
            .where(LLMUsage.model_name.notin_(configured))
            .group_by(LLMUsage.model_name, LLMUsage.provider)
            .order_by(func.count(LLMUsage.id).desc())
        )
        return [
            {
                "model_name": row.model_name,
                "provider": row.provider,
                "call_count": row.call_count,
                "total_tokens": row.total_tokens or 0,
            }
            for row in result.all()
        ]

    @staticmethod
    async def upsert_model_config(
        db: AsyncSession,
        model_name: str,
        provider: str,
        cost_per_1m_input_tokens: float,
        cost_per_1m_output_tokens: float,
        display_name: Optional[str] = None,
    ) -> LLMModelConfig:
        """Create or update a model pricing configuration."""
        stmt = select(LLMModelConfig).where(LLMModelConfig.model_name == model_name)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if config:
            config.provider = provider
            config.cost_per_1m_input_tokens = cost_per_1m_input_tokens
            config.cost_per_1m_output_tokens = cost_per_1m_output_tokens
            if display_name is not None:
                config.display_name = display_name
        else:
            config = LLMModelConfig(
                model_name=model_name,
                display_name=display_name or model_name,
                provider=provider,
                cost_per_1m_input_tokens=cost_per_1m_input_tokens,
                cost_per_1m_output_tokens=cost_per_1m_output_tokens,
            )
            db.add(config)

        await db.commit()
        await db.refresh(config)
        return config

    @staticmethod
    async def delete_model_config(db: AsyncSession, model_name: str) -> bool:
        """Delete a model pricing configuration. Returns True if deleted."""
        stmt = select(LLMModelConfig).where(LLMModelConfig.model_name == model_name)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()
        if config:
            await db.delete(config)
            await db.commit()
            return True
        return False

    @staticmethod
    async def ensure_default_configs(db: AsyncSession):
        """No-op. Model pricing is user-managed via the admin API."""
        pass
