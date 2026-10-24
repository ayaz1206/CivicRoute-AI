"""Verify LLM + embedding provider configuration (M5).

Reports which providers are configured and whether credentials are present,
WITHOUT printing any secret. For real providers it makes one tiny live call to
confirm connectivity; failures are reported as messages, never as a traceback
containing a key.

Usage:
    python -m app.llm.verify
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.embeddings.base import EmbeddingError
from app.embeddings.factory import get_embedding_provider
from app.llm.base import LLMError
from app.llm.factory import get_llm_provider


async def main() -> None:
    settings = get_settings()
    print("Provider configuration (secrets never shown):")
    print(f"  LLM_PROVIDER       : {settings.llm_provider}")
    print(f"  LLM_MODEL          : {settings.llm_model or '(provider default)'}")
    print(f"  EMBEDDING_PROVIDER : {settings.embedding_provider}")
    print(f"  EMBEDDING_MODEL    : {settings.embedding_model or '(provider default)'}")
    print(f"  EMBEDDING_DIM      : {settings.embedding_dim}")
    key_present = bool(settings.llm_api_key)
    print(f"  LLM_API_KEY present: {key_present}")

    real_llm = settings.llm_provider.lower() in ("openai", "anthropic")
    real_embed = settings.embedding_provider.lower() in ("openai",)
    if (real_llm or real_embed) and not key_present:
        print("\nERROR: a real provider is configured but LLM_API_KEY is not set.")
        return

    # LLM connectivity check.
    try:
        llm = get_llm_provider()
        out = await llm.complete_json(
            system="Reply with JSON.",
            user="Say ok.",
            schema_hint={"ok": True},
        )
        print(f"\nLLM check OK ({llm.name}/{getattr(llm, 'model', None)}): {out!r}")
    except LLMError as exc:
        print(f"\nLLM check FAILED ({settings.llm_provider}): {exc}")

    # Embedding connectivity check.
    try:
        emb = get_embedding_provider()
        vecs = await emb.embed(["connectivity check"])
        print(
            f"Embedding check OK ({emb.name}/{emb.model}): "
            f"dim={len(vecs[0])} (configured {emb.dim})"
        )
        if len(vecs[0]) != emb.dim:
            print("  WARNING: returned dimension != configured EMBEDDING_DIM.")
    except EmbeddingError as exc:
        print(f"Embedding check FAILED ({settings.embedding_provider}): {exc}")


if __name__ == "__main__":
    asyncio.run(main())
