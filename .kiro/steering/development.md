# Development — Conventions, Commands & Safeguards

## Local setup

Prerequisites: Python 3.11+ (developed on 3.13), Node.js 20+, Docker + Compose.
Full instructions live in `docs/SETUP.md`; the end-to-end demo walkthrough is in
`docs/DEMO.md`.

Database (PostgreSQL 16 + pgvector, host port 5433):
```bash
cd infra && docker compose up -d
```

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # defaults are offline (fake providers); no secrets
alembic upgrade head
python -m app.seed              # Boston city + departments
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

## Common commands

Backend:
- Tests: `pytest` (from `backend/`).
- Lint: `ruff check .`  ·  autofix: `ruff check --fix .`
- Migrations: `alembic upgrade head`, `alembic revision --autogenerate -m "..."`,
  `alembic downgrade -1`.
- Seed demo data: `python -m app.demo`.
- Boston 311 ingestion: `python -m app.ingestion.cli --max 5000`.
- Provider connectivity check (no secrets printed): `python -m app.llm.verify`.
- Evaluation: `python -m app.eval.run`; duplicate pairs: `python -m app.eval.dup_eval`.
- Safe re-embedding after an embedding-model/dimension change:
  `python -m app.embeddings.reembed --check` then `python -m app.embeddings.reembed`.

Frontend:
- Type check: `npm run typecheck`
- Production build: `npm run build`
- Lint: `npm run lint`

## Conventions

- **Backend layering**: routers (`app/api`) stay thin and delegate to services
  (`app/services`); models in `app/models`, Pydantic schemas in `app/schemas`.
  Business rules live in services, not routers.
- **Async throughout**: FastAPI + async SQLAlchemy + asyncpg.
- **Settings**: all configuration via `app/core/config.py` (pydantic-settings);
  documented in `.env.example`. Never hardcode secrets; API keys are
  environment-only and `.env` is git-ignored.
- **Migrations are the source of truth** for schema; `alembic/env.py` imports
  app metadata. The pgvector HNSW index is maintained by hand in migrations and
  excluded from autogenerate.
- **Providers are configurable and default to offline**: `LLM_PROVIDER=fake`
  and `EMBEDDING_PROVIDER=fake` let the whole system (and the test suite) run
  with no network or credentials. `EMBEDDING_DIM` must match the DB vector
  column; changing the embedding model requires the re-embedding procedure.
- **Lint/style**: ruff (line length 100). Keep imports ordered; prefer the
  existing patterns already in the module you are editing.
- **Frontend**: TypeScript strict; use the typed client in `src/lib/api.ts`;
  style with Tailwind and the theme CSS variables in `globals.css` (readable in
  light and dark modes) rather than hardcoded colors.

## Testing

- The backend suite is pytest + pytest-asyncio and runs against the Dockerized
  database, so start Postgres and apply migrations before running it.
- Tests are hermetic for AI: a conftest fixture forces the deterministic `fake`
  LLM/embedding providers at the configured dimension, so the suite never calls
  a real API or depends on the developer's `.env`.
- Coverage spans: complaint lifecycle and status transitions, auth + RBAC,
  admin gating (including the production hard-rule), the agent workflow
  (transitions, malformed LLM output, provider failures, persistence, review
  severity), human review decisions, duplicate ranking/thresholds/location
  verdicts/privacy, clarification loops, ingestion idempotency, analytics,
  and rate-limit/LLM-retry safeguards.
- Run `npm run typecheck` and `npm run build` for the frontend after UI changes.

## Human-in-the-loop safeguards

These are core product invariants and must be preserved:
- **AI never writes final complaint data directly.** The triage graph writes
  only to the `agent_*` tables; AI-proposed category/priority/department are
  applied to a complaint only when a human approves or overrides the
  recommendation (in the review service).
- **Duplicates are never auto-merged.** Detection produces ranked PENDING
  candidate links with evidence; a human must confirm or reject, and confirming
  records the relationship without merging or closing either complaint.
- **Review gating**: low-confidence or high-risk recommendations are flagged
  (`review_severity`) so staff can prioritize them; all recommendations still
  require explicit human action.
- **No invented data**: the clarification/duplicate logic never fabricates
  addresses or coordinates; missing location is treated as unknown, not as a
  mismatch.
- **Privacy**: resident PII (name/email) is excluded from the public tracking
  endpoint and from duplicate-candidate responses.
- **Separation of concerns in data**: historical Boston 311 records are
  reference-only and are never modified by the live complaint workflow.

## AI-assisted development note

This project was developed with the Kiro CLI agent acting as an AI
pair-programmer across its milestones (scaffolding, implementation, migrations,
tests, and evaluation). Only capabilities that exist in the codebase are
documented here; no functionality is claimed that is not present in the source.
