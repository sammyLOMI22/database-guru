"""OpenAI-compatible LLM provider base class.

Works with any server that implements the OpenAI chat/completions API:
  - OpenAI direct
  - LM Studio (local)
  - vLLM (local)
  - Any OpenAI-compatible endpoint

Uses httpx directly to avoid pulling in the openai SDK as a hard dependency.
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


class OpenAICompatibleProvider(BaseLLMProvider):
    """Base provider for any OpenAI-compatible API.

    Subclasses only need to set provider_name, data_locality, and
    optionally override auth headers or endpoint construction.
    """

    provider_name = "openai_compat"
    data_locality = DataLocality.LOCAL  # Overridden by subclasses

    def __init__(
        self,
        base_url: str = "http://localhost:1234",
        api_key: Optional[str] = None,
        default_model: str = "default",
        org_id: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.org_id = org_id
        self._timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers. Override for provider-specific auth."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.org_id:
            headers["OpenAI-Organization"] = self.org_id
        return headers

    async def connect(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._build_headers(),
            timeout=httpx.Timeout(self._timeout, connect=10.0),
        )
        logger.info(
            f"{self.provider_name} provider connected: {self.base_url} "
            f"(model: {self.default_model})"
        )

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info(f"{self.provider_name} provider disconnected")

    async def _ensure_client(self) -> None:
        if not self.client:
            await self.connect()

    # -- Chat Completions (primary path) --

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ConnectTimeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _chat_completions_raw(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        **kwargs,
    ) -> dict[str, Any]:
        await self._ensure_client()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        # Pass through extra kwargs (top_p, stop, etc.)
        for k, v in kwargs.items():
            if v is not None:
                payload[k] = v

        response = await self.client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    def _parse_chat_response(self, raw: dict[str, Any], model: str) -> LLMResponse:
        """Parse an OpenAI-format chat completion response."""
        choices = raw.get("choices", [])
        text = ""
        if choices:
            text = choices[0].get("message", {}).get("content", "")

        usage = raw.get("usage", {})
        return LLMResponse(
            text=text,
            raw_response=raw,
            model=raw.get("model", model),
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
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
        raw = await self._chat_completions_raw(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return self._parse_chat_response(raw, model)

    # -- Generate (wraps chat with a single user message) --

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    # -- Health Check --

    async def health_check(self) -> ProviderHealth:
        try:
            await self._ensure_client()
            response = await self.client.get("/v1/models")
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
        try:
            await self._ensure_client()
            response = await self.client.get("/v1/models")
            response.raise_for_status()
            data = response.json()
            return [
                ModelInfo(name=m["id"], provider=self.provider_name)
                for m in data.get("data", [])
            ]
        except Exception as e:
            logger.error(f"Failed to list models from {self.provider_name}: {e}")
            return []

    # -- Embeddings --

    async def embeddings(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> Optional[list[float]]:
        try:
            await self._ensure_client()
            model = model or self.default_model
            response = await self.client.post(
                "/v1/embeddings",
                json={"model": model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            embeddings_list = data.get("data", [])
            if embeddings_list:
                return embeddings_list[0].get("embedding")
            return None
        except Exception as e:
            logger.error(f"{self.provider_name} embeddings error: {e}")
            return None
