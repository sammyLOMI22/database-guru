"""TrackedLLMClient — wraps any BaseLLMProvider with usage tracking.

Exposes the same generate()/chat() signature as the original OllamaClient
so all 44+ existing callers continue working with zero changes.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.providers.base import BaseLLMProvider, LLMResponse
from src.observability import tracing as _tracing
from src.services.llm_usage_tracker import llm_usage_tracker

logger = logging.getLogger(__name__)


class TrackedLLMClient:
    """Wraps a BaseLLMProvider and adds LLM usage tracking.

    The generate() and chat() methods match the original OllamaClient
    signature exactly, including tracking parameters (db, agent_type, etc.)
    and the return_full_response flag.
    """

    def __init__(self, provider: BaseLLMProvider):
        self._provider = provider

    @property
    def provider(self) -> BaseLLMProvider:
        return self._provider

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    # -- Backward-compat properties expected by callers --

    @property
    def base_url(self) -> str:
        return getattr(self._provider, "base_url", "")

    @property
    def model(self) -> str:
        return getattr(self._provider, "default_model", "")

    @property
    def client(self) -> Any:
        """Some callers check `if not ollama.client:` before using."""
        return getattr(self._provider, "client", True)

    @property
    def settings(self) -> Any:
        return getattr(self._provider, "settings", None)

    # -- Lifecycle --

    async def connect(self) -> None:
        await self._provider.connect()

    async def disconnect(self) -> None:
        await self._provider.disconnect()

    # -- Generate (matches original OllamaClient signature) --

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.1,
        stream: bool = False,
        return_full_response: bool = False,
        db: Optional[AsyncSession] = None,
        agent_type: str = "unknown",
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        chat_message_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Generate text completion with optional usage tracking.

        Returns:
            If return_full_response=True: dict (raw provider response)
            If return_full_response=False: str (generated text)
        """
        provider_name = self._provider.provider_name
        model_name = model or getattr(self._provider, "default_model", "unknown")
        try:
            if db:
                with _tracing.llm_call_span(
                    provider=provider_name,
                    model=model_name,
                    agent_type=agent_type,
                ):
                    async with llm_usage_tracker.track_call(
                        db=db,
                        agent_type=agent_type,
                        model_name=model_name,
                        llm_method="generate",
                        prompt=prompt,
                        provider=provider_name,
                        query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                        chat_message_id=chat_message_id,
                        agent_name=agent_name,
                        data_locality=self._provider.data_locality.value,
                    ) as tracking:
                        llm_response = await self._provider.generate(
                            prompt=prompt,
                            model=model,
                            system=system,
                            temperature=temperature,
                            **kwargs,
                        )
                        tracking.set_response(llm_response.text, llm_response.raw_response)

                        if return_full_response:
                            return self._to_legacy_generate_dict(llm_response)
                        return llm_response.text
            else:
                with _tracing.llm_call_span(
                    provider=provider_name,
                    model=model_name,
                    agent_type=agent_type,
                ):
                    llm_response = await self._provider.generate(
                        prompt=prompt,
                        model=model,
                        system=system,
                        temperature=temperature,
                        **kwargs,
                    )
                    if return_full_response:
                        return self._to_legacy_generate_dict(llm_response)
                    return llm_response.text

        except Exception as e:
            logger.error(f"{self._provider.provider_name} generation error: {e}")
            raise

    # -- Chat (matches original OllamaClient signature) --

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        return_full_response: bool = False,
        db: Optional[AsyncSession] = None,
        agent_type: str = "unknown",
        query_history_id: Optional[int] = None,
        chat_session_id: Optional[str] = None,
        chat_message_id: Optional[int] = None,
        agent_name: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Chat completion with optional usage tracking.

        Returns:
            If return_full_response=True: dict (raw provider response)
            If return_full_response=False: str (assistant message text)
        """
        provider_name = self._provider.provider_name
        model_name = model or getattr(self._provider, "default_model", "unknown")
        try:
            if db:
                prompt_text = "\n".join(
                    f"{m['role']}: {m['content']}" for m in messages
                )

                with _tracing.llm_call_span(
                    provider=provider_name,
                    model=model_name,
                    agent_type=agent_type,
                ):
                    async with llm_usage_tracker.track_call(
                        db=db,
                        agent_type=agent_type,
                        model_name=model_name,
                        llm_method="chat",
                        prompt=prompt_text,
                        provider=provider_name,
                        query_history_id=query_history_id,
                        chat_session_id=chat_session_id,
                        chat_message_id=chat_message_id,
                        agent_name=agent_name,
                        data_locality=self._provider.data_locality.value,
                    ) as tracking:
                        llm_response = await self._provider.chat(
                            messages=messages,
                            model=model,
                            temperature=temperature,
                            **kwargs,
                        )
                        tracking.set_response(llm_response.text, llm_response.raw_response)

                        if return_full_response:
                            return self._to_legacy_chat_dict(llm_response)
                        return llm_response.text
            else:
                with _tracing.llm_call_span(
                    provider=provider_name,
                    model=model_name,
                    agent_type=agent_type,
                ):
                    llm_response = await self._provider.chat(
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        **kwargs,
                    )
                    if return_full_response:
                        return self._to_legacy_chat_dict(llm_response)
                    return llm_response.text

        except Exception as e:
            logger.error(f"{self._provider.provider_name} chat error: {e}")
            raise

    # -- Other methods (delegate to provider) --

    async def health_check(self) -> bool:
        result = await self._provider.health_check()
        return result.healthy

    async def list_models(self) -> List[str]:
        models = await self._provider.list_models()
        return [m.name for m in models]

    async def embeddings(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> Optional[List[float]]:
        return await self._provider.embeddings(text=text, model=model)

    async def pull_model(self, model: str) -> bool:
        """Pull a model — only works for providers that support it (e.g. Ollama)."""
        pull_fn = getattr(self._provider, "pull_model", None)
        if pull_fn is None:
            logger.warning(
                f"Provider {self._provider.provider_name} does not support pull_model"
            )
            return False
        return await pull_fn(model)

    # -- Legacy dict conversion --

    @staticmethod
    def _to_legacy_generate_dict(resp: LLMResponse) -> Dict[str, Any]:
        """Convert LLMResponse to the dict format callers expect from
        OllamaClient.generate(return_full_response=True).

        The raw_response already contains the full provider dict, so
        callers that access keys like 'response', 'prompt_eval_count',
        'eval_count' will find them there.
        """
        return resp.raw_response

    @staticmethod
    def _to_legacy_chat_dict(resp: LLMResponse) -> Dict[str, Any]:
        """Convert LLMResponse to the dict format callers expect from
        OllamaClient.chat(return_full_response=True).
        """
        return resp.raw_response
