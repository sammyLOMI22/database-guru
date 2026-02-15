"""Ollama LLM client for Database Guru"""
import logging
from typing import Optional, Dict, Any, List
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from src.config.settings import Settings
from src.services.llm_usage_tracker import llm_usage_tracker

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama LLM"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0, connect=5.0),
        )
        logger.info(f"✅ Ollama client initialized: {self.base_url} (model: {self.model})")

    async def disconnect(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            logger.info("Ollama client disconnected")

    async def health_check(self) -> bool:
        """Check if Ollama is available"""
        try:
            if not self.client:
                await self.connect()

            response = await self.client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available models"""
        try:
            if not self.client:
                await self.connect()

            response = await self.client.get("/api/tags")
            response.raise_for_status()

            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _generate_internal(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.1,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Internal generate implementation that always returns full response"""
        if not self.client:
            await self.connect()

        model = model or self.model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                **kwargs,
            },
        }

        if system:
            payload["system"] = system

        logger.debug(f"Generating with {model}: {prompt[:100]}...")

        response = await self.client.post("/api/generate", json=payload)
        response.raise_for_status()

        return response.json()

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
        """
        Generate text completion from Ollama (with optional tracking)
        """
        try:
            if db:
                model_name = model or self.model
                async with llm_usage_tracker.track_call(
                    db=db,
                    agent_type=agent_type,
                    model_name=model_name,
                    llm_method="generate",
                    prompt=prompt,
                    provider="ollama",
                    query_history_id=query_history_id,
                    chat_session_id=chat_session_id,
                    chat_message_id=chat_message_id,
                    agent_name=agent_name,
                ) as tracking:
                    result_dict = await self._generate_internal(
                        prompt=prompt, model=model, system=system,
                        temperature=temperature, stream=stream, **kwargs
                    )
                    generated_text = result_dict.get("response", "")
                    tracking.set_response(generated_text, result_dict)

                    if return_full_response:
                        return result_dict
                    return generated_text
            else:
                result_dict = await self._generate_internal(
                    prompt=prompt, model=model, system=system,
                    temperature=temperature, stream=stream, **kwargs
                )
                if return_full_response:
                    return result_dict
                return result_dict.get("response", "")

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _chat_internal(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs,
    ) -> Dict[str, Any]:
        """Internal chat implementation that always returns full response"""
        if not self.client:
            await self.connect()

        model = model or self.model

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                **kwargs,
            },
        }

        logger.debug(f"Chat with {model}: {len(messages)} messages")

        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()

        return response.json()

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
        """
        Chat completion with conversation history (with optional tracking)
        """
        try:
            if db:
                model_name = model or self.model
                # Convert messages to prompt string for token estimation
                prompt_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)

                async with llm_usage_tracker.track_call(
                    db=db,
                    agent_type=agent_type,
                    model_name=model_name,
                    llm_method="chat",
                    prompt=prompt_text,
                    provider="ollama",
                    query_history_id=query_history_id,
                    chat_session_id=chat_session_id,
                    chat_message_id=chat_message_id,
                    agent_name=agent_name,
                ) as tracking:
                    result_dict = await self._chat_internal(
                        messages=messages, model=model,
                        temperature=temperature, **kwargs
                    )
                    assistant_message = result_dict.get("message", {}).get("content", "")
                    tracking.set_response(assistant_message, result_dict)

                    if return_full_response:
                        return result_dict
                    return assistant_message
            else:
                result_dict = await self._chat_internal(
                    messages=messages, model=model,
                    temperature=temperature, **kwargs
                )
                if return_full_response:
                    return result_dict
                return result_dict.get("message", {}).get("content", "")

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama chat error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    async def pull_model(self, model: str) -> bool:
        """
        Pull/download a model from Ollama library

        Args:
            model: Model name to pull

        Returns:
            True if successful
        """
        try:
            if not self.client:
                await self.connect()

            logger.info(f"Pulling model: {model}")

            response = await self.client.post(
                "/api/pull",
                json={"name": model},
                timeout=600.0,  # Model downloads can take time
            )
            response.raise_for_status()

            logger.info(f"✅ Model pulled: {model}")
            return True

        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _embeddings_internal(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Internal embeddings implementation with retry"""
        if not self.client:
            await self.connect()

        model = model or self.model

        response = await self.client.post(
            "/api/embeddings",
            json={"model": model, "prompt": text},
        )
        response.raise_for_status()

        return response.json()

    async def embeddings(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> Optional[List[float]]:
        """
        Generate embeddings for text

        Args:
            text: Text to embed
            model: Model name

        Returns:
            Embedding vector
        """
        try:
            result = await self._embeddings_internal(text=text, model=model)
            return result.get("embedding")

        except Exception as e:
            logger.error(f"Embeddings generation error: {e}")
            return None


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
