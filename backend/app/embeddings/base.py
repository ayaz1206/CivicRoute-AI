"""Embedding provider protocol and errors."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class EmbeddingError(Exception):
    """Raised when an embedding call fails."""


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str
    model: str
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text.

        On any failure, raise :class:`EmbeddingError`.
        """
        ...
