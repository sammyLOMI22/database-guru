"""AWS Bedrock provider — enterprise cloud LLM via AWS.

Data locality: CLOUD_PRIVATE — data stays within the user's AWS account and region.

AWS Bedrock uses:
  - boto3 for SigV4 request signing (required for AWS auth)
  - Converse API (unified across all Bedrock models)
  - Region-scoped endpoints: bedrock-runtime.{region}.amazonaws.com
"""
import logging
from typing import Any, Optional

from src.llm.providers.base import (
    BaseLLMProvider,
    DataLocality,
    LLMResponse,
    ModelInfo,
    ProviderHealth,
)
from src.llm.providers.types import ChatMessage

logger = logging.getLogger(__name__)

# Common Bedrock model IDs
BEDROCK_MODELS = [
    "anthropic.claude-sonnet-4-20250514-v1:0",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-haiku-20241022-v1:0",
    "amazon.nova-pro-v1:0",
    "amazon.nova-lite-v1:0",
    "amazon.nova-micro-v1:0",
    "meta.llama3-1-70b-instruct-v1:0",
    "meta.llama3-1-8b-instruct-v1:0",
    "mistral.mistral-large-2407-v1:0",
]


class AWSBedrockProvider(BaseLLMProvider):
    """AWS Bedrock provider.

    Uses the Bedrock Converse API via boto3 with SigV4 signing.
    Data stays within the user's AWS account and region.
    """

    provider_name = "aws_bedrock"
    data_locality = DataLocality.CLOUD_PRIVATE

    def __init__(
        self,
        region: str = "us-east-1",
        default_model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        session_token: Optional[str] = None,
        profile_name: Optional[str] = None,
    ):
        self.region = region
        self.default_model = default_model
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._session_token = session_token
        self._profile_name = profile_name
        self._client = None  # boto3 bedrock-runtime client

    def _get_boto3_client(self):
        """Create or return the boto3 bedrock-runtime client."""
        if self._client is not None:
            return self._client

        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for AWS Bedrock. "
                "Install it with: pip install boto3"
            )

        kwargs: dict[str, Any] = {"region_name": self.region}
        if self._access_key_id and self._secret_access_key:
            kwargs["aws_access_key_id"] = self._access_key_id
            kwargs["aws_secret_access_key"] = self._secret_access_key
            if self._session_token:
                kwargs["aws_session_token"] = self._session_token

        if self._profile_name:
            session = boto3.Session(profile_name=self._profile_name)
            self._client = session.client("bedrock-runtime", **kwargs)
        else:
            self._client = boto3.client("bedrock-runtime", **kwargs)

        logger.info(
            f"Bedrock client initialized: region={self.region}, "
            f"model={self.default_model}"
        )
        return self._client

    async def connect(self) -> None:
        self._get_boto3_client()

    async def disconnect(self) -> None:
        self._client = None
        logger.info("Bedrock provider disconnected")

    # -- Converse API --

    @staticmethod
    def _messages_to_converse(
        messages: list[ChatMessage],
    ) -> tuple[list[dict[str, Any]], Optional[list[dict[str, Any]]]]:
        """Convert ChatMessage list to Bedrock Converse format.

        Returns (messages, system) where system is extracted from
        system-role messages.
        """
        system_parts = []
        converse_messages = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_parts.append({"text": content})
                continue
            converse_role = "assistant" if role == "assistant" else "user"
            converse_messages.append({
                "role": converse_role,
                "content": [{"text": content}],
            })

        system = system_parts if system_parts else None
        return converse_messages, system

    async def _converse_raw(
        self,
        messages: list[dict[str, Any]],
        model: str,
        system: Optional[list[dict[str, Any]]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> dict[str, Any]:
        import asyncio

        client = self._get_boto3_client()

        kwargs: dict[str, Any] = {
            "modelId": model,
            "messages": messages,
            "inferenceConfig": {"temperature": temperature},
        }
        if max_tokens is not None:
            kwargs["inferenceConfig"]["maxTokens"] = max_tokens
        if system:
            kwargs["system"] = system

        # boto3 is synchronous; run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: client.converse(**kwargs)
        )
        return response

    @staticmethod
    def _extract_text(response: dict[str, Any]) -> str:
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])
        return "".join(block.get("text", "") for block in content)

    @staticmethod
    def _extract_tokens(response: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
        usage = response.get("usage", {})
        return (
            usage.get("inputTokens"),
            usage.get("outputTokens"),
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

    async def chat(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        model = model or self.default_model
        converse_messages, system = self._messages_to_converse(messages)
        raw = await self._converse_raw(
            messages=converse_messages,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
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
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        system_parts = [{"text": system}] if system else None
        raw = await self._converse_raw(
            messages=messages,
            model=model,
            system=system_parts,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self._parse_response(raw, model)

    # -- Health Check --

    async def health_check(self) -> ProviderHealth:
        try:
            self._get_boto3_client()
            raw = await self._converse_raw(
                messages=[{"role": "user", "content": [{"text": "Hello"}]}],
                model=self.default_model,
                system=None,
                temperature=0.0,
                max_tokens=1,
            )
            healthy = "output" in raw
            return ProviderHealth(
                healthy=healthy,
                provider=self.provider_name,
                data_locality=self.data_locality.value,
                message="OK" if healthy else "No output in response",
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
            import asyncio
            import boto3

            # Use bedrock (not bedrock-runtime) for model listing
            kwargs: dict[str, Any] = {"region_name": self.region}
            if self._access_key_id and self._secret_access_key:
                kwargs["aws_access_key_id"] = self._access_key_id
                kwargs["aws_secret_access_key"] = self._secret_access_key

            loop = asyncio.get_event_loop()
            client = boto3.client("bedrock", **kwargs)
            response = await loop.run_in_executor(
                None,
                lambda: client.list_foundation_models(
                    byInferenceType="ON_DEMAND",
                    byOutputModality="TEXT",
                ),
            )
            models = response.get("modelSummaries", [])
            return [
                ModelInfo(
                    name=m.get("modelId", ""),
                    provider=self.provider_name,
                )
                for m in models
            ]
        except Exception as e:
            logger.error(f"Failed to list Bedrock models: {e}")
            return [
                ModelInfo(name=m, provider=self.provider_name)
                for m in BEDROCK_MODELS
            ]
