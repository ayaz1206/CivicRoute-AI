"""Shared HTTP helper for LLM providers with timeout + bounded retries."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.llm.base import LLMError


async def post_with_retries(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    max_retries: int,
) -> dict[str, Any]:
    """POST JSON, retrying transient failures (timeouts, 429, 5xx).

    Raises LLMError on exhaustion or non-retryable errors. Secrets in headers
    are never logged.
    """
    attempt = 0
    last_exc: Exception | None = None
    while attempt <= max_retries:
        try:
            async with httpx.AsyncClient(timeout=timeout) as http:
                resp = await http.post(url, json=payload, headers=headers)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(
                        f"retryable status {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                return resp.json()
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.TransportError) as exc:
            last_exc = exc
            attempt += 1
            if attempt > max_retries:
                break
            await asyncio.sleep(min(2 ** attempt * 0.1, 2.0))  # backoff
        except httpx.HTTPError as exc:  # non-retryable
            raise LLMError(f"LLM request failed: {exc}") from exc
    raise LLMError(f"LLM request failed after {max_retries} retries: {last_exc}")
