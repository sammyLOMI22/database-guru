"""Google Vertex AI provider — enterprise cloud LLM via Google Cloud.

Data locality: CLOUD_PRIVATE — data stays within the user's GCP project and region.

Vertex AI differs from direct Gemini API in:
  - Project/region-scoped endpoints: {region}-aiplatform.googleapis.com
  - Auth via Application Default Credentials (ADC) or service account key
  - REST path: /v1/projects/{project}/locations/{region}/publishers/google/models/{model}:generateContent
  - Response shape uses `candidates[].content.parts[].text`
"""
import json
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

# Well-known Vertex AI models
VERTEX_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]


def _get_adc_token() -> Optional[str]:
    """Get an access token via Application Default Credentials.

    Uses google.auth if available, otherwise returns None.
    """
    try:
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(google.auth.transport.requests.Request())
        return credentials.token
    except Exception as e:
        logger.debug(f"ADC token fetch failed: {e}")
        return None


class GoogleVertexProvider(BaseLLMProvider):
    """Google Vertex AI provider.

    Uses the Vertex AI REST API with Application Default Credentials.
    Data stays within the user's GCP project and region.
    """

    provider_name = "google_vertex"
    data_locality = DataLocality.CLOUD_PRIVATE

    def __init__(
        self,
        project_id: str,
        region: str = "us-central1",
        default_model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.project_id = project_id
        self.region = region
        self.default_model = default_model
        self._api_key = api_key  # Optional: direct API key auth
        self._timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None

    @property
    def _base_url(self) -> str:
        return f"https://{self.region}-aiplatform.googleapis.com"

    def _model_url(self, model: str, action: str = "generateContent") -> str:
        return (
            f"{self._base_url}/v1/projects/{self.project_id}"
            f"/locations/{self.region}/publishers/google"
            f"/models/{model}:{action}"
        )

    async def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        else:
            token = _get_adc_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
            else:
                logger.warning(
                    "No Vertex AI credentials available — "
                    "set GOOGLE_VERTEX_API_KEY or configure ADC"
                )
        return headers

    async def connect(self) -> None:
        headers = await self._build_headers()
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(self._timeout, connect=10.0),
        )
        logger.info(
            f"Vertex AI provider connected: project={self.project_id}, "
            f"region={self.region}, model={self.default_model}"
        )

    async def disconnect(self) -> None:
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info("Vertex AI provider disconnected")

    async def _ensure_client(self) -> None:
        if not self.client:
            await self.connect()

    # -- Generate Content --

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ConnectTimeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _generate_content_raw(
        self,
        contents: list[dict[str, Any]],
        model: str,
        system_instruction: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs,
    ) -> dict[str, Any]:
        await self._ensure_client()
        url = self._model_url(model)

        payload: dict[str, Any] = {"contents": contents}
        generation_config: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens
        payload["generationConfig"] = generation_config

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _extract_text(raw: dict[str, Any]) -> str:
        candidates = raw.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)

    @staticmethod
    def _extract_tokens(raw: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
        usage = raw.get("usageMetadata", {})
        return (
            usage.get("promptTokenCount"),
            usage.get("candidatesTokenCount"),
        )

    def _parse_response(self, raw: dict[str, Any], model: str) -> LLMResponse:
        text = self._extract_text(raw)
        input_tokens, output_tokens = self._extract_tokens(raw)
        return LLMResponse(
            text=text,
            raw_response=raw,
            model=model,
            provider=self.provider_name,
            data_locality=self.data_locality.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    @staticmethod
    def _messages_to_contents(messages: list[ChatMessage]) -> tuple[list[dict], Optional[str]]:
        """Convert ChatMessage list to Vertex AI contents format.

        Vertex uses role="user"/"model" (not "assistant").
        System messages are extracted to systemInstruction.
        """
        system = None
        contents = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                system = msg["content"]
                continue
            vertex_role = "model" if role == "assistant" else "user"
            contents.append({
                "role": vertex_role,
                "parts": [{"text": msg["content"]}],
            })
        return contents, system

    async def chat(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        model = model or self.default_model
        contents, system = self._messages_to_contents(messages)
        raw = await self._generate_content_raw(
            contents=contents,
            model=model,
            system_instruction=system,
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
        model = model or self.default_model
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        raw = await self._generate_content_raw(
            contents=contents,
            model=model,
            system_instruction=system,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return self._parse_response(raw, model)

    # -- Health Check --

    async def health_check(self) -> ProviderHealth:
        try:
            await self._ensure_client()
            url = self._model_url(self.default_model)
            response = await self.client.post(
                url,
                json={
                    "contents": [
                        {"role": "user", "parts": [{"text": "Hello"}]}
                    ],
                    "generationConfig": {"maxOutputTokens": 1},
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
        # Vertex AI model listing requires discovery API; return known catalog
        return [
            ModelInfo(name=m, provider=self.provider_name)
            for m in VERTEX_MODELS
        ]
