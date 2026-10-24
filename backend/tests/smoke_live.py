"""One-shot live smoke check: boots the ASGI app in-process and calls the
health endpoints against the real database. Run manually, not part of pytest.

Usage:
    python tests/smoke_live.py
"""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def main() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://smoke") as c:
        h = await c.get("/health")
        print("GET /health ->", h.status_code, h.json())

        r = await c.get("/health/ready")
        print("GET /health/ready ->", r.status_code, r.json())

        docs = await c.get("/docs")
        print("GET /docs ->", docs.status_code)

        assert h.status_code == 200
        assert r.status_code == 200, "readiness should be 200 against the live DB"
        assert r.json()["database"] == "ok"
        print("SMOKE OK")


if __name__ == "__main__":
    asyncio.run(main())
