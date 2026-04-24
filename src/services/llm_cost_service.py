"""Service for managing LLM model configurations and costs"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select, func, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import LLMModelConfig, LLMUsage

logger = logging.getLogger(__name__)

class LLMCostService:
    """Service for managing LLM model configurations and costs."""

    @staticmethod
    async def get_model_config(
        db: AsyncSession,
        model_name: str,
        provider: Optional[str] = None,
    ) -> Optional[LLMModelConfig]:
        """Fetch configuration for a specific model.

        When provider is supplied, lookups are scoped to that provider so the same
        model name on different providers (e.g. gpt-4o on openai vs azure_openai)
        cannot return the wrong price. Falls back to a provider-agnostic lookup
        only if provider is None (legacy callers).
        """
        # Try exact match first, scoped by provider when available
        conditions = [LLMModelConfig.model_name == model_name]
        if provider is not None:
            conditions.append(LLMModelConfig.provider == provider)
        stmt = select(LLMModelConfig).where(*conditions)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            # Try fuzzy match (e.g. "llama3:latest" -> "llama3")
            # Order by name length to prefer exact prefix matches over longer ones
            base_name = model_name.split(":")[0]
            fuzzy_conditions = [LLMModelConfig.model_name.like(f"{base_name}%")]
            if provider is not None:
                fuzzy_conditions.append(LLMModelConfig.provider == provider)
            stmt = (
                select(LLMModelConfig)
                .where(*fuzzy_conditions)
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
        output_tokens: int,
        provider: Optional[str] = None,
    ) -> float:
        """Calculate the estimated cost in USD for a given model and token counts."""
        config = await LLMCostService.get_model_config(db, model_name, provider)

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
        """Find (model_name, provider) pairs seen in usage with no pricing config."""
        configured_pairs = select(LLMModelConfig.model_name, LLMModelConfig.provider)
        result = await db.execute(
            select(
                LLMUsage.model_name,
                LLMUsage.provider,
                func.count(LLMUsage.id).label("call_count"),
                func.sum(LLMUsage.input_tokens + LLMUsage.output_tokens).label("total_tokens"),
            )
            .where(tuple_(LLMUsage.model_name, LLMUsage.provider).notin_(configured_pairs))
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
        """Create or update a model pricing configuration keyed by (model_name, provider).

        Race-safe: on concurrent create, catches IntegrityError and falls back to update.
        """
        for attempt in range(2):
            stmt = select(LLMModelConfig).where(
                LLMModelConfig.model_name == model_name,
                LLMModelConfig.provider == provider,
            )
            result = await db.execute(stmt)
            config = result.scalar_one_or_none()

            if config:
                config.cost_per_1m_input_tokens = cost_per_1m_input_tokens
                config.cost_per_1m_output_tokens = cost_per_1m_output_tokens
                if display_name is not None:
                    config.display_name = display_name
                try:
                    await db.commit()
                    await db.refresh(config)
                    return config
                except IntegrityError:
                    await db.rollback()
                    if attempt == 1:
                        raise
                    continue

            config = LLMModelConfig(
                model_name=model_name,
                display_name=display_name or model_name,
                provider=provider,
                cost_per_1m_input_tokens=cost_per_1m_input_tokens,
                cost_per_1m_output_tokens=cost_per_1m_output_tokens,
            )
            db.add(config)
            try:
                await db.commit()
                await db.refresh(config)
                return config
            except IntegrityError:
                await db.rollback()
                if attempt == 1:
                    raise

        raise RuntimeError("upsert_model_config failed after retry")

    @staticmethod
    async def delete_model_config(
        db: AsyncSession,
        model_name: str,
        provider: Optional[str] = None,
    ) -> bool:
        """Delete a model pricing configuration. Returns True if deleted.

        If provider is supplied, deletes the exact (model_name, provider) row.
        Otherwise deletes any row matching model_name (legacy compatibility).
        """
        stmt = select(LLMModelConfig).where(LLMModelConfig.model_name == model_name)
        if provider is not None:
            stmt = stmt.where(LLMModelConfig.provider == provider)
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
