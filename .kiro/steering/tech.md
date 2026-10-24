# Tech — Stack & Architecture

All items below reflect what is actually in the repository.

## Stack

Backend (`backend/`):
- Python 3.11+ (developed on 3.13), FastAPI, Uvicorn.
- SQLAlchemy 2.0 (async) with asyncpg; Pydantic v2 + pydantic-settings.
- Alembic for migrations.
- LangGraph for the agent workflow.
- pgvector (`pgvector` SQLAlchemy type) for embeddings.
- httpx for outbound LLM/embedding and Boston 311 API calls.
- passlib[bcrypt] + PyJWT for auth.
- Tooling: pytest + pytest-asyncio, ruff.

Frontend (`frontend/`):
- Next.js (App Router), React, TypeScript, Tailwind CSS.

Database & infra (`infra/`):
- PostgreSQL 16 with the `vector` extension, via the `pgvector/pgvector:pg16`
  Docker image and `docker-compose.yml`. Published on host port 5433 by default.

LLM / embedding providers:
- Configurable via settings. LLM: `fake` (default, deterministic, offline),
  `openai`, or `anthropic`. Embeddings: `fake` (default, 384-dim) or `openai`
  (`text-embedding-3-small`, 1536-dim). API keys are read from environment
  variables and are never committed.

## Architecture

Three tiers plus an agentic core:

```
Next.js (resident + staff UIs)
        │  HTTPS / REST (JSON, Bearer JWT for staff)
FastAPI (routers → services → models)
        │
PostgreSQL + pgvector   ◄── Alembic migrations
        ▲
LangGraph triage graph + configurable LLM/embedding providers
        ▲
Boston 311 Open Data (CKAN API) — ingested into a separate historical table
```

Layering in the backend:
- **API routers** (`app/api/`) — thin HTTP handlers, dependency-injected
  services, auth/role guards, and rate limiting on expensive endpoints.
- **Services** (`app/services/`) — business logic (complaint, agent, review,
  duplicate, clarification, analytics, auth, city). The single place AI-derived
  values are applied to a complaint is the review service, on human approval.
- **Models** (`app/models/`) — SQLAlchemy ORM entities and enums.
- **Schemas** (`app/schemas/`) — Pydantic request/response models.
- **Agent** (`app/agent/`) — LangGraph graph, nodes, routing, categories,
  clarification logic, and evaluation dataset hooks.
- **LLM / embeddings** (`app/llm/`, `app/embeddings/`) — provider protocol,
  factory, fake + real adapters, retry/timeout helper.

Key design principles enforced in code:
- **Multi-tenant**: domain rows are scoped by `city_id`.
- **Live vs. historical separation**: resident complaints live in `complaints`
  (`source = web`); Boston 311 history lives in a dedicated
  `historical_311_requests` table and is never mutated by the live workflow.
- **AI output is separate from complaint data**: triage writes only to the
  `agent_runs` / `agent_steps` / `agent_recommendations` tables; the complaint
  row is changed only when a human approves/overrides a recommendation.
- **Human-in-the-loop**: duplicate links and AI recommendations are always
  PENDING until a human decides; nothing auto-applies or auto-merges.
- **Auditability**: agent runs/steps, status history, and review decisions are
  persisted.

## Security posture

- JWT auth with `staff` / `admin` roles; admin-only user creation.
- Administrative endpoints require a valid token; an unauthenticated
  development fallback exists but is **never** allowed in production.
- Resident tracking is public and PII-free.
- Rate limiting, LLM timeouts, output-token caps, and bounded retries guard the
  expensive AI endpoints. Secrets are environment-only.

## Boston 311 data

Ingested from the City of Boston CKAN Open Data API into
`historical_311_requests`. Ingestion is validated and idempotent (upsert on the
311 `case_enquiry_id`). This data powers analytics and informs department
routing; it is never embedded into the live duplicate-detection corpus.
