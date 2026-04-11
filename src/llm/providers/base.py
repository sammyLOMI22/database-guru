"""Base class and core types for LLM providers."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.llm.providers.types import ChatMessage

logger = logging.getLogger(__name__)


class DataLocality(Enum):
    """Where user data goes when sent to a provider.

    LOCAL — data stays on the user's machine/network (Ollama, LM Studio, vLLM).
    CLOUD_PRIVATE — data stays within user's cloud tenant (Azure, Bedrock, Vertex).
    CLOUD_PUBLIC — data is sent to a third-party API (OpenAI, Anthropic).
    """
    LOCAL = "local"
    CLOUD_PRIVATE = "cloud_private"
    CLOUD_PUBLIC = "cloud_public"


# Security level ordering for enforcement
_SECURITY_ALLOWS: dict[str, set[DataLocality]] = {
    "local_only": {DataLocality.LOCAL},
    "cloud_private": {DataLocality.LOCAL, DataLocality.CLOUD_PRIVATE},
    "unrestricted": {DataLocality.LOCAL, DataLocality.CLOUD_PRIVATE, DataLocality.CLOUD_PUBLIC},
}


def is_locality_allowed(data_locality: DataLocality, security_level: str) -> bool:
    """Check whether a provider's data locality is permitted by the security level."""
    allowed = _SECURITY_ALLOWS.get(security_level, _SECURITY_ALLOWS["local_only"])
    return data_locality in allowed


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""
    text: str
    raw_response: dict[str, Any]
    model: str
    provider: str
    data_locality: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


@dataclass
class ProviderHealth:
    """Health check result for a provider."""
    healthy: bool
    provider: str
    data_locality: str
    message: str = ""


@dataclass
class ModelInfo:
    """Information about an available model."""
    name: str
    provider: str
    size: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers.

    Every provider must declare:
    - provider_name: unique identifier (e.g. "ollama", "openai")
    - data_locality: where user data goes (LOCAL, CLOUD_PRIVATE, CLOUD_PUBLIC)

    Subclasses implement the raw LLM call logic. Tracking, security gating,
    and fallback are handled by TrackedLLMClient and ProviderRegistry.
    """

    provider_name: str
    data_locality: DataLocality

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a text completion."""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Chat completion with conversation history."""
        ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check if the provider is reachable and operational."""
        ...

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """List available models from this provider."""
        ...

    async def embeddings(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> Optional[list[float]]:
        """Generate embeddings. Optional — returns None if unsupported."""
        return None

    async def connect(self) -> None:
        """Initialize connections/clients. Called before first use."""
        pass

    async def disconnect(self) -> None:
        """Clean up connections/clients."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider_name}, locality={self.data_locality.value})"
