"""Select an LLM provider from settings."""

from __future__ import annotations

from app.core.config import get_settings
from app.llm.base import LLMError, LLMProvider
from app.llm.fake import FakeLLMProvider


def get_llm_provider() -> LLMProvider:
    """Instantiate the configured provider.

    Defaults to the deterministic ``fake`` provider so the system runs without
    network access or credentials. ``openai``/``anthropic`` require LLM_API_KEY.
    """
    settings = get_settings()
    provider = (settings.llm_provider or "fake").lower()

    if provider == "fake":
        return FakeLLMProvider(model=settings.llm_model)
    if provider == "openai":
        from app.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.llm_api_key or "", model=settings.llm_model
        )
    if provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=settings.llm_api_key or "", model=settings.llm_model
        )
    raise LLMError(f"Unknown LLM provider: {settings.llm_provider!r}")
