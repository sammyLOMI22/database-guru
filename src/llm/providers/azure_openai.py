"""Azure OpenAI provider — enterprise cloud LLM via Azure deployments.

Data locality: CLOUD_PRIVATE — data stays within the user's Azure tenant.

Azure OpenAI differs from direct OpenAI in:
  - Deployment-based URLs: /openai/deployments/{deployment}/chat/completions
  - API key via `api-key` header (not `Authorization: Bearer`)
  - Required `api-version` query parameter
  - Model list comes from deployments, not /v1/models
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


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI Service provider.

    Uses deployment-based endpoints within the user's Azure tenant.
    Data stays within the user's Azure subscription and region.
    """

    provider_name = "azure_openai"
    data_locality = DataLocality.CLOUD_PRIVATE

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment_name: str,
        api_version: str = "2024-02-15-preview",
        default_model: Optional[str] = None,
        timeout: float = 120.0,
    ):
        # endpoint: https://<resource>.openai.azure.com
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.deployment_name = deployment_name
        self.api_version = api_version
        self.default_model = default_model or deployment_name
        self._timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

    def _deployment_url(self, deployment: Optional[str] = None) -> str:
        """Build the deployment-specific chat completions URL."""
        dep = deployment or self.deployment_name
        return (
            f"{self.endpoint}/openai/deployments/{dep}"
            f"/chat/completions?api-version={self.api_version}"
        )

    async def connect(self) -> None:
        self.client = httpx.AsyncClient(
            headers=self._build_headers(),
            timeout=httpx.Timeout(self._timeout, connect=10.0),
        )
        logger.info(
            f"Azure OpenAI provider connected: {self.endpoint} "
            f"(deployment: {self.deployment_name})"
        )

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("Azure OpenAI provider disconnected")

    async def _ensure_client(self) -> None:
        if not self.client:
            await self.connect()

    # -- Chat Completions --

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
        deployment: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs,
    ) -> dict[str, Any]:
        await self._ensure_client()
        url = self._deployment_url(deployment)

        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        for k, v in kwargs.items():
            if v is not None:
                payload[k] = v

        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def _parse_response(self, raw: dict[str, Any], model: str) -> LLMResponse:
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
        # model param maps to deployment name for Azure
        deployment = model or self.deployment_name
        raw = await self._chat_completions_raw(
            messages=messages,
            deployment=deployment,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return self._parse_response(raw, deployment)

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
            # Use a lightweight chat completion to verify connectivity
            url = self._deployment_url()
            response = await self.client.post(
                url,
                json={
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

    # -- List Models (deployments) --

    async def list_models(self) -> list[ModelInfo]:
        try:
            await self._ensure_client()
            url = (
                f"{self.endpoint}/openai/deployments"
                f"?api-version={self.api_version}"
            )
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return [
                ModelInfo(
                    name=d.get("id", d.get("deployment_id", "")),
                    provider=self.provider_name,
                )
                for d in data.get("data", [])
            ]
        except Exception as e:
            logger.error(f"Failed to list Azure deployments: {e}")
            # Fall back to just reporting the configured deployment
            return [ModelInfo(name=self.deployment_name, provider=self.provider_name)]
