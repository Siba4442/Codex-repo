# backend/services/llm_client.py
"""LLM client wrapper for OpenRouter/OpenAI."""

from contextvars import ContextVar
from typing import Any, Dict, List, Type

from openai import AsyncOpenAI
from pydantic import BaseModel

# Context variable for restaurant name (works across async operations)
_restaurant_name: ContextVar[str] = ContextVar('restaurant_name', default=None)


class LLMClientError(RuntimeError):
    """LLM client error."""

    pass


class LLMClient:
    """Wrapper around OpenRouter chat completions."""

    def __init__(
        self, api_key: str, provider: str = "OpenRouter", model: str = None
    ):
        self.api_key = api_key
        self.model = model
        self.provider = provider
        if not self.model:
            raise LLMClientError("Model must be specified")

    def _get_client(self) -> AsyncOpenAI:
        """Create client with dynamic headers based on context."""
        restaurant_name = _restaurant_name.get()
        x_title = f"OrderArt / {restaurant_name}" if restaurant_name else "OrderArt Menu Extraction"
        
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost:8080",
                "X-Title": x_title,
                "X-User-Id": "orderart"
            }
        )

    def json_schema_format(self, model_cls: Type[BaseModel]) -> Dict[str, Any]:
        """Generate JSON schema response format."""
        return {
            "type": "json_schema",
            "json_schema": {
                "name": model_cls.__name__,
                "schema": model_cls.model_json_schema(),
                "strict": True,
            },
        }

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        response_format: Dict[str, Any] = None,
    ):
        """Call LLM with messages."""
        try:
            # Create client with current context headers
            client = self._get_client()
            
            return await client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format=response_format,
            )
        except Exception as e:
            raise LLMClientError(f"LLM call failed: {e}") from e


# Singleton
_llm_client: LLMClient = None


def set_restaurant_context(restaurant_name: str):
    """Set restaurant name in context for dynamic headers."""
    _restaurant_name.set(restaurant_name)


def get_llm_client() -> LLMClient:
    """Get cached LLM client instance."""
    global _llm_client
    if _llm_client is None:
        from backend.config import get_settings

        settings = get_settings()
        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            raise RuntimeError(
                "API key for OpenRouter not found in environment variables."
            )
        _llm_client = LLMClient(
            api_key=api_key,
            provider="OpenRouter",
            model=settings.OPENROUTER_DEFAULT_MODEL,
        )
    return _llm_client
