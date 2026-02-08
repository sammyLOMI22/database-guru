"""Service for managing LLM model configurations and costs"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import LLMModelConfig

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
            base_name = model_name.split(":")[0]
            stmt = select(LLMModelConfig).where(LLMModelConfig.model_name.like(f"{base_name}%"))
            result = await db.execute(stmt)
            config = result.scalar_one_or_none()

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
    async def ensure_default_configs(db: AsyncSession):
        """Ensure default model configurations exist in the database."""
        defaults = [
            {
                "model_name": "llama3",
                "display_name": "Llama 3 (Local)",
                "provider": "ollama",
                "cost_per_1m_input_tokens": 0.0,
                "cost_per_1m_output_tokens": 0.0,
            },
            {
                "model_name": "gpt-4o",
                "display_name": "GPT-4o",
                "provider": "openai",
                "cost_per_1m_input_tokens": 5.0,
                "cost_per_1m_output_tokens": 15.0,
            },
            {
                "model_name": "gpt-3.5-turbo",
                "display_name": "GPT-3.5 Turbo",
                "provider": "openai",
                "cost_per_1m_input_tokens": 0.5,
                "cost_per_1m_output_tokens": 1.5,
            },
            {
                "model_name": "claude-3-5-sonnet",
                "display_name": "Claude 3.5 Sonnet",
                "provider": "anthropic",
                "cost_per_1m_input_tokens": 3.0,
                "cost_per_1m_output_tokens": 15.0,
            }
        ]

        for d in defaults:
            stmt = select(LLMModelConfig).where(LLMModelConfig.model_name == d["model_name"])
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                config = LLMModelConfig(**d)
                db.add(config)

        await db.commit()
