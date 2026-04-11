"""vLLM provider — local inference via OpenAI-compatible API.

Data locality: LOCAL — data stays on the user's machine.
"""
import logging
from typing import Optional

from src.llm.providers.base import DataLocality
from src.llm.providers.openai_compat import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class VLLMProvider(OpenAICompatibleProvider):
    """vLLM provider (local OpenAI-compatible server).

    vLLM exposes an OpenAI-compatible API, typically at
    http://localhost:8000. No API key required by default.
    Data never leaves the machine.
    """

    provider_name = "vllm"
    data_locality = DataLocality.LOCAL

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        default_model: str = "default",
        api_key: Optional[str] = None,
        timeout: float = 120.0,
    ):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            default_model=default_model,
            timeout=timeout,
        )
