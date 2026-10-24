"""Tests for rate limiting and LLM safeguards (M5)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import ratelimit
from app.core.config import Settings, get_settings
from app.main import create_app

API = "/api"


@pytest.fixture(autouse=True)
def _reset_rl():
    ratelimit.reset()
    yield
    ratelimit.reset()


@pytest.fixture
async def limited_client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    # Dev env (admin gate open) + tiny rate limit to exercise 429 quickly.
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        app_env="development",
        rate_limit_per_minute=2,
        rate_limit_enabled=True,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_rate_limit_blocks_after_threshold(
    limited_client: AsyncClient, make_complaint
) -> None:
    cid = await make_complaint()
    # Limit is 2/min; the 3rd triage call should be rejected with 429.
    r1 = await limited_client.post(f"{API}/agent/complaints/{cid}/triage")
    r2 = await limited_client.post(f"{API}/agent/complaints/{cid}/triage")
    r3 = await limited_client.post(f"{API}/agent/complaints/{cid}/triage")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert "Retry-After" in r3.headers


async def test_llm_retry_helper_succeeds_after_transient(monkeypatch) -> None:
    """post_with_retries retries a transient 503 then succeeds."""
    import httpx

    from app.llm.http import post_with_retries

    calls = {"n": 0}

    class _Resp:
        def __init__(self, status):
            self.status_code = status
            self.request = httpx.Request("POST", "http://x")

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("err", request=self.request, response=self)

        def json(self):
            return {"ok": True}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                return _Resp(503)  # transient
            return _Resp(200)

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    out = await post_with_retries("http://x", {}, {}, timeout=1.0, max_retries=2)
    assert out == {"ok": True}
    assert calls["n"] == 2


async def test_llm_retry_helper_exhausts(monkeypatch) -> None:
    import httpx

    from app.llm.base import LLMError
    from app.llm.http import post_with_retries

    class _Resp:
        status_code = 503

        def __init__(self):
            self.request = httpx.Request("POST", "http://x")

        def raise_for_status(self):
            raise httpx.HTTPStatusError("err", request=self.request, response=self)

        def json(self):
            return {}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    with pytest.raises(LLMError):
        await post_with_retries("http://x", {}, {}, timeout=0.1, max_retries=1)
