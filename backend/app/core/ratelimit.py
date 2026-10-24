"""Minimal in-process rate limiter (M5).

A fixed-window per-client counter guarding expensive endpoints (LLM/embedding
triggered). This is intentionally simple and process-local — suitable for a
single-instance demo. A production deployment would use a shared store (Redis).
"""

from __future__ import annotations

import time

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings

# client_key -> (window_start_epoch, count)
_WINDOW = 60.0
_counters: dict[str, tuple[float, int]] = {}


def _client_key(request: Request) -> str:
    # Prefer the authenticated subject if present; else client host.
    auth = request.headers.get("authorization", "")
    if auth:
        return f"tok:{hash(auth)}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


def rate_limit(
    request: Request, settings: Settings = Depends(get_settings)
) -> None:
    """FastAPI dependency: raise 429 when the per-minute limit is exceeded."""
    if not settings.rate_limit_enabled:
        return
    limit = settings.rate_limit_per_minute
    key = _client_key(request)
    now = time.time()
    start, count = _counters.get(key, (now, 0))
    if now - start >= _WINDOW:
        start, count = now, 0
    count += 1
    _counters[key] = (start, count)
    if count > limit:
        retry = int(_WINDOW - (now - start))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({limit}/min). Retry in {retry}s.",
            headers={"Retry-After": str(max(1, retry))},
        )


def reset() -> None:
    """Clear counters (used by tests)."""
    _counters.clear()
