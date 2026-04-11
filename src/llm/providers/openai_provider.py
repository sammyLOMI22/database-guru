"""OpenAI direct API provider.

Data locality: CLOUD_PUBLIC — prompts are sent to OpenAI's API servers.
"""
import logging
from typing import Optional

from src.llm.providers.base import DataLocality
from src.llm.providers.openai_compat import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI API provider (GPT-4, GPT-4o, GPT-3.5-turbo, etc.).

    Uses the standard OpenAI chat completions API.
    Data is sent to OpenAI's cloud servers.
    """

    provider_name = "openai"
    data_locality = DataLocality.CLOUD_PUBLIC

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4o",
        org_id: Optional[str] = None,
        base_url: str = "https://api.openai.com",
        timeout: float = 120.0,
    ):
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            default_model=default_model,
            org_id=org_id,
            timeout=timeout,
        )
