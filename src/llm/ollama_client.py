"""Ollama LLM client for Database Guru — backward-compatible shim.

This module preserves the original OllamaClient interface and
get_ollama_client() factory. Under the hood it delegates to
OllamaProvider + TrackedLLMClient from the new provider abstraction.

All existing callers (44+ files) continue to work unchanged.
"""
import logging
from typing import Optional

from src.config.settings import Settings
from src.llm.providers.ollama import OllamaProvider
from src.llm.tracked_client import TrackedLLMClient

logger = logging.getLogger(__name__)


class OllamaClient(TrackedLLMClient):
    """Backward-compatible alias for TrackedLLMClient wrapping OllamaProvider.

    Preserves the original class name so isinstance checks and type hints
    in existing code continue to work.
    """

    def __init__(self, settings: Settings):
        provider = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            default_model=settings.OLLAMA_MODEL,
        )
        super().__init__(provider)
        self._settings = settings

    @property
    def settings(self) -> Settings:
        return self._settings


# Global Ollama client instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client(settings: Optional[Settings] = None) -> OllamaClient:
    """Get or create the global Ollama client instance"""
    global _ollama_client

    if _ollama_client is None:
        if settings is None:
            settings = Settings()
        _ollama_client = OllamaClient(settings)

    return _ollama_client
