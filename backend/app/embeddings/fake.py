"""Deterministic, offline embedding provider.

Produces stable unit vectors from token-hashing (a lightweight bag-of-words
hashing embedding). Not semantically perfect, but deterministic and good enough
that similar texts (shared tokens) score higher than unrelated ones — which is
what the duplicate-detection tests and offline demos need. No network or keys.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN = re.compile(r"[a-z0-9]+")


class FakeEmbeddingProvider:
    name = "fake"

    def __init__(self, model: str | None = None, dim: int = 384) -> None:
        self.model = model or "fake-hash-embed"
        self.dim = dim

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _TOKEN.findall(text.lower())
        for tok in tokens:
            h = hashlib.sha1(tok.encode()).digest()
            idx = int.from_bytes(h[:4], "big") % self.dim
            sign = 1.0 if h[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            # Avoid a zero vector (undefined cosine); use a fixed unit vector.
            vec[0] = 1.0
            return vec
        return [v / norm for v in vec]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]
