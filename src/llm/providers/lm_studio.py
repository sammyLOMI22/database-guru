"""LM Studio provider — local inference via OpenAI-compatible API.

Data locality: LOCAL — data stays on the user's machine.
"""
import logging
from typing import Optional

from src.llm.providers.base import DataLocality
from src.llm.providers.openai_compat import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio provider (local OpenAI-compatible server).

    LM Studio runs models locally and exposes an OpenAI-compatible
    API at http://localhost:1234 by default. No API key required.
    Data never leaves the machine.
    """

    provider_name = "lm_studio"
    data_locality = DataLocality.LOCAL

    def __init__(
        self,
        base_url: str = "http://localhost:1234",
        default_model: str = "default",
        timeout: float = 120.0,
    ):
        super().__init__(
            base_url=base_url,
            api_key=None,
            default_model=default_model,
            timeout=timeout,
        )
