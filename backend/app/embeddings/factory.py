"""Select an embedding provider from settings."""

from __future__ import annotations

from app.core.config import get_settings
from app.embeddings.base import EmbeddingError, EmbeddingProvider
from app.embeddings.fake import FakeEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = (settings.embedding_provider or "fake").lower()
    if provider == "fake":
        return FakeEmbeddingProvider(
            model=settings.embedding_model, dim=settings.embedding_dim
        )
    if provider == "openai":
        from app.embeddings.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            api_key=settings.llm_api_key or "", model=settings.embedding_model
        )
    raise EmbeddingError(f"Unknown embedding provider: {settings.embedding_provider!r}")
