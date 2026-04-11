"""Ollama LLM provider — local model inference via Ollama API."""
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


class OllamaProvider(BaseLLMProvider):
    """LLM provider for Ollama (local inference).

    Data never leaves the user's machine.
    """

    provider_name = "ollama"
    data_locality = DataLocality.LOCAL

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.2:latest",
    ):
        self.base_url = base_url
        self.default_model = default_model
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0, connect=5.0),
        )
        logger.info(f"Ollama provider connected: {self.base_url} (model: {self.default_model})")

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("Ollama provider disconnected")

    async def _ensure_client(self) -> None:
        if not self.client:
            await self.connect()

    # -- Generate --

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ConnectTimeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _generate_raw(
        self,
        prompt: str,
        model: str,
        system: Optional[str],
        temperature: float,
        stream: bool,
        **kwargs,
    ) -> dict[str, Any]:
        await self._ensure_client()
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {"temperature": temperature, **kwargs},
        }
        if system:
            payload["system"] = system
        response = await self.client.post("/api/generate", json=payload)
        response.raise_for_status()
        return response.json()

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        model = model or self.default_model
        extra = {}
        if max_tokens is not None:
            extra["num_predict"] = max_tokens
        raw = await self._generate_raw(
            prompt=prompt,
            model=model,
            system=system,
            temperature=temperature,
            stream=False,
            **extra,
            **kwargs,
        )
        return LLMResponse(
            text=raw.get("response", ""),
            raw_response=raw,
            model=model,
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            input_tokens=raw.get("prompt_eval_count"),
            output_tokens=raw.get("eval_count"),
        )

    # -- Chat --

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ConnectTimeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _chat_raw(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        **kwargs,
    ) -> dict[str, Any]:
        await self._ensure_client()
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, **kwargs},
        }
        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        return response.json()

    async def chat(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        model = model or self.default_model
        extra = {}
        if max_tokens is not None:
            extra["num_predict"] = max_tokens
        raw = await self._chat_raw(
            messages=messages,
            model=model,
            temperature=temperature,
            **extra,
            **kwargs,
        )
        text = raw.get("message", {}).get("content", "")
        return LLMResponse(
            text=text,
            raw_response=raw,
            model=model,
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            input_tokens=raw.get("prompt_eval_count"),
            output_tokens=raw.get("eval_count"),
        )

    # -- Health / Models / Embeddings --

    async def health_check(self) -> ProviderHealth:
        try:
            await self._ensure_client()
            response = await self.client.get("/api/tags")
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

    async def list_models(self) -> list[ModelInfo]:
        try:
            await self._ensure_client()
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [
                ModelInfo(name=m["name"], provider=self.provider_name)
                for m in data.get("models", [])
            ]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def embeddings(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> Optional[list[float]]:
        try:
            await self._ensure_client()
            model = model or self.default_model
            response = await self.client.post(
                "/api/embeddings",
                json={"model": model, "prompt": text},
            )
            response.raise_for_status()
            return response.json().get("embedding")
        except Exception as e:
            logger.error(f"Ollama embeddings error: {e}")
            return None

    async def pull_model(self, model: str) -> bool:
        """Pull/download a model from the Ollama library."""
        try:
            await self._ensure_client()
            logger.info(f"Pulling model: {model}")
            response = await self.client.post(
                "/api/pull",
                json={"name": model},
                timeout=600.0,
            )
            response.raise_for_status()
            logger.info(f"Model pulled: {model}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False
