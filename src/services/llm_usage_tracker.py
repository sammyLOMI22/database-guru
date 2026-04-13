"""Centralized LLM usage tracking service"""
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import tiktoken
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import LLMUsage

logger = logging.getLogger(__name__)

class LLMUsageTracker:
    """Centralized LLM usage tracking service."""

    def __init__(self):
        self._encoder = None  # Lazy-loaded tiktoken encoder

    @property
    def encoder(self):
        if self._encoder is None:
            try:
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Failed to load tiktoken encoder: {e}")
                self._encoder = None
        return self._encoder

    def estimate_tokens(self, text: str) -> tuple[int, str]:
        """Estimate token count for text. Returns (count, method)."""
        if not text:
            return 0, "empty"

        if self.encoder:
            try:
                return len(self.encoder.encode(text)), "tiktoken"
            except Exception:
                pass

        # Fallback: rough estimate (4 chars per token average)
        return len(text) // 4, "estimated"

    def extract_tokens(self, response: dict, provider: str) -> tuple[Optional[int], Optional[int]]:
        """
        Extract token counts from LLM response based on provider.
        Supports: ollama, openai, anthropic, azure, google_vertex, aws_bedrock
        """
        if not response:
            return None, None

        if provider == "ollama":
            input_tokens = response.get("prompt_eval_count")
            output_tokens = response.get("eval_count")
            return input_tokens, output_tokens

        elif provider in ("openai", "azure", "azure_openai", "lm_studio", "vllm"):
            usage = response.get("usage", {})
            return usage.get("prompt_tokens"), usage.get("completion_tokens")

        elif provider == "anthropic":
            usage = response.get("usage", {})
            return usage.get("input_tokens"), usage.get("output_tokens")

        elif provider == "google_vertex":
            usage = response.get("usageMetadata", {})
            return usage.get("promptTokenCount"), usage.get("candidatesTokenCount")

        elif provider == "aws_bedrock":
            usage = response.get("usage", {})
            return usage.get("inputTokens"), usage.get("outputTokens")

        return None, None

    @asynccontextmanager
    async def track_call(
        self,
        db: AsyncSession,
        agent_type: str,
        model_name: str,
        llm_method: str,
        prompt: str,
        provider: str = "ollama",
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        chat_message_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        data_locality: Optional[str] = None,
    ):
        """
        Context manager to track an LLM call.

        Usage:
            async with tracker.track_call(db, "sql_generator", model, "generate", prompt, provider="ollama") as tracking:
                response = await ollama.generate(...)
                tracking.set_response(response_text, provider_response_dict)
        """
        start_time = time.time()
        tracking = _TrackingContext(
            tracker=self,
            db=db,
            agent_type=agent_type,
            model_name=model_name,
            llm_method=llm_method,
            prompt=prompt,
            provider=provider,
            query_history_id=query_history_id,
            chat_session_id=chat_session_id,
            chat_message_id=chat_message_id,
            agent_name=agent_name,
            metadata=metadata,
            start_time=start_time,
            data_locality=data_locality,
        )

        try:
            yield tracking
        except Exception as e:
            tracking.set_error(str(e))
            raise
        finally:
            await tracking.save()


class _TrackingContext:
    """Internal context for a single LLM call being tracked."""

    def __init__(self, tracker, db, agent_type, model_name, llm_method, prompt,
                 provider, query_history_id, chat_session_id, chat_message_id,
                 agent_name, metadata, start_time, data_locality=None):
        self.tracker = tracker
        self.db = db
        self.agent_type = agent_type
        self.model_name = model_name
        self.llm_method = llm_method
        self.prompt = prompt
        self.provider = provider
        self.query_history_id = query_history_id
        self.chat_session_id = chat_session_id
        self.chat_message_id = chat_message_id
        self.agent_name = agent_name
        self.metadata = metadata or {}
        self.start_time = start_time
        self.data_locality = data_locality

        self.response_text: Optional[str] = None
        self.provider_response: Optional[dict] = None
        self.error_message: Optional[str] = None
        self.success = True

    def set_response(self, response_text: str, provider_response: Optional[dict] = None):
        """Set the response from the LLM call."""
        self.response_text = response_text
        self.provider_response = provider_response

    def set_error(self, error_message: str):
        """Mark the call as failed."""
        self.success = False
        self.error_message = error_message

    async def save(self):
        """Save the usage record to the database."""
        end_time = time.time()
        response_time_ms = (end_time - self.start_time) * 1000

        # Calculate tokens
        input_tokens, input_method = self.tracker.estimate_tokens(self.prompt)
        output_tokens, output_method = 0, "empty"
        token_method = input_method

        if self.response_text:
            output_tokens, output_method = self.tracker.estimate_tokens(self.response_text)

        # Try to get native token counts
        if self.provider_response:
            native_input, native_output = self.tracker.extract_tokens(self.provider_response, self.provider)
            if native_input is not None:
                input_tokens = native_input
                token_method = f"{self.provider}_native"
            if native_output is not None:
                output_tokens = native_output
                token_method = f"{self.provider}_native"

        # Calculate estimated cost
        from src.services.llm_cost_service import LLMCostService
        estimated_cost = await LLMCostService.calculate_cost(
            self.db, self.model_name, input_tokens, output_tokens
        )

        # Create record
        usage_record = LLMUsage(
            query_history_id=self.query_history_id,
            chat_session_id=self.chat_session_id,
            chat_message_id=self.chat_message_id,
            agent_type=self.agent_type,
            agent_name=self.agent_name,
            provider=self.provider,
            data_locality=self.data_locality,
            model_name=self.model_name,
            llm_method=self.llm_method,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            token_estimation_method=token_method,
            request_timestamp=datetime.now(timezone.utc),
            response_time_ms=response_time_ms,
            prompt_summary=self.prompt[:500] if self.prompt else None,
            response_summary=self.response_text[:500] if self.response_text else None,
            success=self.success,
            error_message=self.error_message,
            estimated_cost_usd=estimated_cost,
            metadata_json=self.metadata,
        )

        try:
            async with self.db.begin_nested():
                self.db.add(usage_record)
                await self.db.flush()
        except Exception as e:
            logger.error(f"Failed to save LLM usage record: {e}")

        return usage_record


# Global instance
llm_usage_tracker = LLMUsageTracker()
