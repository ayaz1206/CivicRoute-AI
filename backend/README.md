# CivicRoute AI — Backend

FastAPI application. M0 foundation: app factory, settings, async DB layer,
Alembic migrations, health/readiness endpoints, and tests.

## Develop

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Layout

```
app/
  core/config.py   # pydantic-settings Settings
  db/base.py       # DeclarativeBase
  db/session.py    # async engine + session factory + get_session dependency
  api/health.py    # /health and /health/ready
  main.py          # create_app() factory
alembic/           # migration environment + versions
tests/             # pytest suite
```

## Endpoints

### Health (unversioned)

| Method | Path            | Purpose                                   |
| ------ | --------------- | ----------------------------------------- |
| GET    | `/health`       | Liveness — process is up                  |
| GET    | `/health/ready` | Readiness — verifies DB connectivity      |

### Domain API (under `/api`)

| Method | Path                                   | Purpose                                 |
| ------ | -------------------------------------- | --------------------------------------- |
| GET    | `/api/cities`                          | List cities                             |
| GET    | `/api/cities/{id}/departments`         | List a city's departments               |
| POST   | `/api/complaints`                      | Submit a complaint (resident)           |
| GET    | `/api/complaints`                      | List live complaints (filter/paginate)  |
| GET    | `/api/complaints/track/{code}`         | Track by public code (with timeline)    |
| GET    | `/api/complaints/{id}`                 | Get a complaint with its timeline       |
| POST   | `/api/complaints/{id}/status`          | Change status (staff)                   |
| PATCH  | `/api/complaints/{id}/assignment`      | Set category/priority/department (staff)|
| GET    | `/api/analytics/overview`              | Historical 311 analytics for a city     |

## Seed reference data

```bash
python -m app.seed   # creates Boston + departments (no complaints, no 311 data)
```

## Boston 311 ingestion (M2)

Pulls recent Boston 311 records from the CKAN Open Data API into the dedicated
`historical_311_requests` table. Validated and idempotent (upsert on
`case_enquiry_id`); safe to re-run.

```bash
python -m app.ingestion.cli --max 5000   # default max is 5000
```

Configuration (see `.env.example`): `BOSTON_311_RESOURCE_ID`,
`BOSTON_311_MAX_RECORDS`, `BOSTON_311_PAGE_SIZE`.

## Agentic triage (M3)

A LangGraph workflow (`extract → classify → prioritize → route → gate`) triages a
complaint and produces an auditable `AgentRecommendation`. AI output is kept
separate from the complaint; values are applied only after a human approves or
overrides them.

- LLM provider is configurable via `LLM_PROVIDER` (`fake` default — deterministic,
  offline; or `openai`/`anthropic` with `LLM_API_KEY`).
- Low-confidence or high-risk (urgent) recommendations are routed to the human
  review queue. Confidence threshold: `AGENT_REVIEW_THRESHOLD`.
- Endpoints (all admin-gated): `POST /api/agent/complaints/{id}/triage`,
  `GET /api/agent/runs/{id}`, `GET /api/agent/review-queue`,
  `POST /api/agent/recommendations/{id}/decision`.

No semantic duplicate detection, embeddings, notifications, or external
integrations are implemented.

### Evaluating the workflow against a real model

`python -m app.agent.evaluate` runs the triage workflow over representative
Boston-style complaints with the *configured* provider and reports model,
outputs, confidence, latency, and (for real providers) token usage + an
approximate cost. API keys are read from the environment and never logged.

```bash
# Offline (deterministic, default):
python -m app.agent.evaluate
# Real model (requires a key in the environment):
LLM_PROVIDER=openai LLM_MODEL=gpt-4o-mini LLM_API_KEY=... python -m app.agent.evaluate
```

> Real-model telemetry (latency, tokens, cost) is only produced when a real
> provider key is configured. Without one, the harness runs the `fake` provider
> and reports no token/cost figures.

## Duplicate detection & clarification (M4)

- Live complaints are embedded on submission (best-effort, non-blocking) into
  `complaint_embeddings` (pgvector, HNSW cosine index) with model/version metadata.
  Embedding provider is configurable (`EMBEDDING_PROVIDER`: `fake` default, `openai`).
- `POST /api/duplicates/complaints/{id}/detect` returns a ranked list of possible
  duplicates (live complaints only) blending similarity, category compatibility,
  location evidence, and status. Results are **candidates**; staff confirm/reject
  via `POST /api/duplicates/links/{id}/decision`. Complaints are **never auto-merged**.
- `POST /api/duplicates/complaints/{id}/clarifications/generate` detects missing
  info (location, detail) and asks targeted questions. Residents answer via the
  public `GET/POST /api/clarifications/...` routes (keyed by tracking code).

Guarantees: historical 311 data is never embedded or searched here; no addresses
or coordinates are invented (location answers are stored as resident-provided
text only); duplicate suggestions never expose other residents' PII.

## Test

```bash
pytest
ruff check .
```
