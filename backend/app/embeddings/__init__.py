"""Configurable embedding provider abstraction (M4).

Mirrors the LLM provider design: a small interface with a deterministic offline
``fake`` default and real adapters selected via settings. Embeddings power
pgvector semantic similarity search for duplicate detection over LIVE complaints
only (historical 311 data is never embedded or searched here).
"""

from app.embeddings.base import EmbeddingError, EmbeddingProvider
from app.embeddings.factory import get_embedding_provider

__all__ = ["EmbeddingProvider", "EmbeddingError", "get_embedding_provider"]
