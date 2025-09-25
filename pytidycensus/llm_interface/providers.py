"""LLM provider implementations for Census Assistant.

Focused on reliable, cost-effective options with local fallbacks.
"""

import json
import logging
import warnings
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str, **kwargs):
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat completion."""

    @abstractmethod
    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured output matching a schema."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available/configured."""


class OpenAIProvider(LLMProvider):
    """OpenAI provider - reliable but requires API key."""

    def __init__(self, model: str = "gpt-3.5-turbo", api_key: Optional[str] = None, **kwargs):
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                import openai

                if self.api_key:
                    self._client = openai.OpenAI(api_key=self.api_key)
                else:
                    # Try to use environment variable
                    self._client = openai.OpenAI()
            except ImportError:
                raise ImportError("OpenAI package not installed. Install with: pip install openai")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                raise
        return self._client

    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        try:
            self._get_client()
            return True
        except:
            return False

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs,
    ) -> str:
        """Generate chat completion using OpenAI."""
        try:
            client = self._get_client()

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI chat completion failed: {e}")
            raise

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured output using OpenAI function calling."""
        try:
            client = self._get_client()

            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that always responds with valid JSON matching the requested schema.",
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nRespond with JSON matching this schema: {json.dumps(schema)}",
                },
            ]

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            logger.error(f"OpenAI structured output failed: {e}")
            raise


class OllamaProvider(LLMProvider):
    """Ollama provider for local models - free but requires local setup."""

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434", **kwargs):
        super().__init__(model, **kwargs)
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        """Lazy initialization of Ollama client."""
        if self._client is None:
            try:
                import ollama

                self._client = ollama.Client(host=self.base_url)
            except ImportError:
                raise ImportError("Ollama package not installed. Install with: pip install ollama")
        return self._client

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            client = self._get_client()
            # Try to list models to test connectivity
            client.list()
            return True
        except:
            return False

    async def chat_completion(
        self, messages: List[Dict[str, str]], temperature: float = 0.7, **kwargs
    ) -> str:
        """Generate chat completion using Ollama."""
        try:
            client = self._get_client()

            response = client.chat(
                model=self.model, messages=messages, options={"temperature": temperature, **kwargs}
            )

            return response["message"]["content"]

        except Exception as e:
            logger.error(f"Ollama chat completion failed: {e}")
            raise

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured output using Ollama."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Always respond with valid JSON matching the requested schema. Do not include any text outside the JSON.",
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nRespond with JSON matching this schema: {json.dumps(schema)}",
                },
            ]

            response = await self.chat_completion(messages, temperature=0.1)

            # Try to extract JSON from response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:-3].strip()
            elif response.startswith("```"):
                response = response[3:-3].strip()

            return json.loads(response)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Ollama response: {e}")
            # Return a default structure if parsing fails
            return {"error": "Failed to parse structured output", "raw_response": response}
        except Exception as e:
            logger.error(f"Ollama structured output failed: {e}")
            raise


class LLMManager:
    """Manages multiple LLM providers with automatic fallbacks."""

    def __init__(self, providers: List[LLMProvider]):
        self.providers = providers
        self.available_providers = [p for p in providers if p.is_available()]

        if not self.available_providers:
            warnings.warn(
                "No LLM providers are available. Please install and configure "
                "either OpenAI (with API key) or Ollama (local)."
            )

    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Try providers in order until one succeeds."""
        if not self.available_providers:
            raise RuntimeError("No LLM providers available")

        for provider in self.available_providers:
            try:
                return await provider.chat_completion(messages, **kwargs)
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")
                continue

        raise RuntimeError("All LLM providers failed")

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Try providers in order until one succeeds."""
        if not self.available_providers:
            raise RuntimeError("No LLM providers available")

        for provider in self.available_providers:
            try:
                return await provider.structured_output(prompt, schema)
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")
                continue

        raise RuntimeError("All LLM providers failed")


def create_default_llm_manager(openai_api_key: Optional[str] = None) -> LLMManager:
    """Create a default LLM manager with cost-effective options."""
    providers = [
        # Try OpenAI first (reliable, but requires API key)
        OpenAIProvider(model="gpt-3.5-turbo", api_key=openai_api_key),
        # Fallback to local Ollama (free, but requires local setup)
        OllamaProvider(model="llama3.2"),  # Good balance of size/performance
    ]

    return LLMManager(providers)
