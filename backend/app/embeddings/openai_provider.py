"""OpenAI embeddings adapter (text-embedding-3-small by default)."""

from __future__ import annotations

import httpx

from app.embeddings.base import EmbeddingError

_API_URL = "https://api.openai.com/v1/embeddings"
_DIMS = {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072}


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str | None = None, timeout: float = 30.0):
        if not api_key:
            raise EmbeddingError("OpenAI embeddings require LLM_API_KEY")
        self.api_key = api_key
        self.model = model or "text-embedding-3-small"
        self.dim = _DIMS.get(self.model, 1536)
        self.timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http:
                resp = await http.post(_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return [row["embedding"] for row in data["data"]]
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            raise EmbeddingError(f"OpenAI embeddings request failed: {exc}") from exc
