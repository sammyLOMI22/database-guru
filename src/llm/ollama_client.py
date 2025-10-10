"""Ollama LLM client for Database Guru"""
import logging
from typing import Optional, Dict, Any, List
import httpx
from src.config.settings import Settings

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

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.1,
        stream: bool = False,
        **kwargs,
    ) -> str:
        """
        Generate text completion from Ollama

        Args:
            prompt: User prompt
            model: Model name (uses default if not specified)
            system: System prompt
            temperature: Temperature for generation (0.0-1.0)
            stream: Whether to stream response
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        try:
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

            result = response.json()
            generated_text = result.get("response", "")

            logger.debug(f"Generated {len(generated_text)} characters")
            return generated_text

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs,
    ) -> str:
        """
        Chat completion with conversation history

        Args:
            messages: List of message dicts with "role" and "content"
            model: Model name
            temperature: Temperature for generation
            **kwargs: Additional options

        Returns:
            Assistant's response
        """
        try:
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

            result = response.json()
            assistant_message = result.get("message", {}).get("content", "")

            return assistant_message

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
            if not self.client:
                await self.connect()

            model = model or self.model

            response = await self.client.post(
                "/api/embeddings",
                json={"model": model, "prompt": text},
            )
            response.raise_for_status()

            result = response.json()
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
