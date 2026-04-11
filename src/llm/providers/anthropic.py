"""Anthropic provider — Claude models via the Messages API.

Data locality: CLOUD_PUBLIC — data is sent to Anthropic's API servers.

Anthropic's Messages API differs from OpenAI in:
  - System prompt is a top-level parameter, not a message
  - Response uses content blocks (list of {type, text}) not a single string
  - Auth via `x-api-key` header
  - Token usage: input_tokens / output_tokens (not prompt_tokens / completion_tokens)
"""
import logging
from typing import Any, Optional

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.llm.providers.base import (
    BaseLLMProvider,
    DataLocality,
    LLMResponse,
    ModelInfo,
    ProviderHealth,
)
from src.llm.providers.types import ChatMessage

logger = logging.getLogger(__name__)

# Models available via Anthropic API
ANTHROPIC_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-haiku-4-20250414",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
]


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API provider (Claude models).

    Uses the Messages API at https://api.anthropic.com/v1/messages.
    Data is sent to Anthropic's cloud servers.
    """

    provider_name = "anthropic"
    data_locality = DataLocality.CLOUD_PUBLIC

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-sonnet-4-20250514",
        base_url: str = "https://api.anthropic.com",
        api_version: str = "2023-06-01",
        max_tokens_default: int = 4096,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.api_version = api_version
        self.max_tokens_default = max_tokens_default
        self._timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
        }

    async def connect(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._build_headers(),
            timeout=httpx.Timeout(self._timeout, connect=10.0),
        )
        logger.info(
            f"Anthropic provider connected: {self.base_url} "
            f"(model: {self.default_model})"
        )

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("Anthropic provider disconnected")

    async def _ensure_client(self) -> None:
        if not self.client:
            await self.connect()

    # -- Messages API --

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ConnectTimeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _messages_raw(
        self,
        messages: list[dict[str, str]],
        model: str,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> dict[str, Any]:
        await self._ensure_client()

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            payload["system"] = system
        for k, v in kwargs.items():
            if v is not None:
                payload[k] = v

        response = await self.client.post("/v1/messages", json=payload)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _extract_text(raw: dict[str, Any]) -> str:
        """Extract text from Anthropic content blocks."""
        content = raw.get("content", [])
        text_parts = []
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return "".join(text_parts)

    def _parse_response(self, raw: dict[str, Any], model: str) -> LLMResponse:
        text = self._extract_text(raw)
        usage = raw.get("usage", {})
        return LLMResponse(
            text=text,
            raw_response=raw,
            model=raw.get("model", model),
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens_default

        # Anthropic: system prompt must be extracted from messages
        # and passed as a top-level parameter
        system = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered_messages.append(msg)

        raw = await self._messages_raw(
            messages=filtered_messages,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return self._parse_response(raw, model)

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens_default

        raw = await self._messages_raw(
            messages=messages,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return self._parse_response(raw, model)

    # -- Health Check --

    async def health_check(self) -> ProviderHealth:
        try:
            await self._ensure_client()
            # Use a minimal messages call to verify connectivity
            response = await self.client.post(
                "/v1/messages",
                json={
                    "model": self.default_model,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 1,
                },
            )
            healthy = response.status_code == 200
            return ProviderHealth(
                healthy=healthy,
                provider=self.provider_name,
                data_locality=self.data_locality.value,
                message="OK" if healthy else f"HTTP {response.status_code}",
            )
        except Exception as e:
            return ProviderHealth(
                healthy=False,
                provider=self.provider_name,
                data_locality=self.data_locality.value,
                message=str(e),
            )

    # -- List Models --

    async def list_models(self) -> list[ModelInfo]:
        # Anthropic doesn't have a models listing endpoint;
        # return the known model catalog
        return [
            ModelInfo(name=m, provider=self.provider_name)
            for m in ANTHROPIC_MODELS
        ]
