"""Shared types for LLM providers."""
from dataclasses import dataclass, field
from typing import Any, Optional, TypedDict


class ChatMessage(TypedDict):
    """A single message in a chat conversation."""
    role: str       # "system", "user", "assistant"
    content: str


@dataclass
class ProviderConfig:
    """Configuration for instantiating an LLM provider."""
    provider_name: str
    enabled: bool = False
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    default_model: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
