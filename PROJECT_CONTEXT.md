# CivicRoute AI — Project Context

A living reference for the project's architecture, stack, features, schema, API,
known issues, and priorities. Everything here is derived from the actual
codebase and verified project state (not aspirational).

Last reviewed against: latest `main` commit `f1bd2f9 "Major UI Changes"`, plus
uncommitted working-tree changes noted under "Verified project state."

---

## 1. Overview

CivicRoute AI is an agentic, AI-assisted civic complaint management and routing
platform. Residents submit non-emergency complaints; a LangGraph workflow backed
by a configurable LLM extracts details, classifies, prioritizes, and routes each
complaint to a department. Every AI output is a **recommendation that a human
must approve** before it is applied. The system is multi-city (tenant-scoped by
`city_id`), with Boston as the first city; historical Boston 311 Open Data is
used for analytics/routing signals and kept separate from live complaints.

---

## 2. Architecture

Three tiers plus an agentic core:

```
Next.js (resident + staff UIs)
      │  REST/JSON over HTTP; staff calls carry a Bearer JWT
FastAPI  (routers → services → models)
      │
PostgreSQL 16 + pgvector   ◄── Alembic migrations
      ▲
LangGraph triage graph + configurable LLM & embedding providers
      ▲
Boston 311 Open Data (CKAN API) → separate historical_311_requests table
```

Backend layering (strict):
- `app/api/*` — thin HTTP routers; dependency-injected services; auth/role and
  rate-limit guards. Domain errors are mapped centrally in `main.py`
  (`NotFoundError`→404, `ValidationError`→409).
- `app/services/*` — business logic. **The review service is the only place
  AI-derived values are written onto a complaint**, and only on human approval.
- `app/models/*` — SQLAlchemy 2.0 ORM entities + enums.
- `app/schemas/*` — Pydantic v2 request/response models.
- `app/agent/*` — LangGraph graph/nodes, routing, categories, clarification,
  evaluation dataset.
- `app/llm/*`, `app/embeddings/*` — provider protocol, factory, fake + real
  adapters, retry/timeout helper.
- `app/ingestion/*` — Boston 311 CKAN client, parser, idempotent ingest CLI.
- `app/eval/*` — evaluation harnesses (classification/routing metrics, duplicate
  pairs, end-to-end demo).

Core invariants (enforced in code):
- Multi-tenant scoping by `city_id`.
- Live vs. historical separation: live complaints in `complaints`
  (`source=web`); Boston 311 in `historical_311_requests` (never mutated by the
  live workflow).
- AI output is separate from complaint data (`agent_*` tables).
- Human-in-the-loop: recommendations and duplicate links are PENDING until a
  human decides; **no auto-apply, no auto-merge**.

---

## 3. Technology stack

Backend (`backend/`, Python 3.11+, developed on 3.13):
- FastAPI, Uvicorn
- SQLAlchemy 2.0 async + asyncpg
- Pydantic v2 + pydantic-settings
- Alembic (migrations)
- LangGraph (agent workflow)
- pgvector (embeddings / similarity)
- httpx (LLM/embedding + Boston 311 calls)
- passlib[bcrypt] (pinned bcrypt==4.0.1) + PyJWT (auth)
- pytest + pytest-asyncio, ruff (dev)

Frontend (`frontend/`):
- Next.js 15 (App Router), React 19, TypeScript (strict), Tailwind CSS 3.4
- No component/icon library (custom design-system components + inline SVG icons)
- Inter via `next/font`

Infra (`infra/`):
- PostgreSQL 16 + `vector` via `pgvector/pgvector:pg16` Docker image,
  `docker-compose.yml`, host port **5433**.

LLM/embedding providers (configurable, default offline):
- LLM: `fake` (default, deterministic), `openai`, `anthropic`
- Embeddings: `fake` (default, 384-dim) or `openai` `text-embedding-3-small`
  (1536-dim). The DB embedding column is currently **vector(1536)** (migration
  `a2c5e1f09b34`); `EMBEDDING_DIM` must match the column.
- API keys come from the environment only; `.env` is git-ignored.

---

## 4. Implemented features

Resident:
- Submit a complaint (title, description, optional location text/coords, optional
  reporter contact). Embedding is generated best-effort on submit.
- Public tracking by code: status, PII-free detail, status timeline.
- Answer clarification questions (persisted, resumable).

AI / agentic (LangGraph: extract → classify → prioritize → route → gate):
- Classification into a validated category set.
- Priority with an explicit four-level rubric (low/medium/high/urgent; urgent
  reserved for immediate safety threats) + rationale.
- Department routing via validated category→department mapping blended with
  historical 311 patterns.
- Confidence scores + review-severity gating (`routine`/`low_confidence`/
  `high_risk`).
- Configurable LLM provider; auditable runs/steps/recommendations.

Duplicate detection:
- pgvector cosine KNN over live complaints, blended with category compatibility
  and **location-aware** evidence (coordinates when present; normalized
  location-text otherwise; missing = unknown, never a mismatch).
- Decision uses a combined score vs. threshold (default 0.78) with a retrieval
  floor (0.6). Human confirm/reject only; never auto-merges.

Staff / admin:
- JWT auth (`staff`/`admin`); admin-only user creation.
- Dashboard: filter live complaints; detail panel distinguishing **assigned
  (approved) fields** from a **pending AI recommendation**; run triage; run
  duplicate detection (loading/empty/error/results states); manage status;
  timeline.
- AI review queue: flagged vs. routine; confidence bars; approve/override/reject.
- Boston 311 analytics: totals + category/neighborhood/department/status
  breakdowns + daily trend.
- Auth-aware navigation: avatar/initials + profile dropdown (name, email, role;
  My Profile, Staff Dashboard, Sign out); `/profile` page.

Data & evaluation:
- Idempotent Boston 311 ingestion (`app.ingestion.cli`).
- Evaluation harnesses (`app.eval.run`, `app.eval.dup_eval`, `app.eval.e2e_demo`)
  and provider verification (`app.llm.verify`), safe re-embedding
  (`app.embeddings.reembed`), seed/demo scripts (`app.seed`, `app.demo`).

Explicitly NOT implemented (by design): external notifications (email/SMS),
real city-system integrations, automatic duplicate merging.

---

## 5. Database schema

PostgreSQL + pgvector. Tables (via Alembic migrations, in order: `0001_baseline`
→ `58f6523669c0` M1 → `35e9f4442af9` historical → `8f767f9b297a` M3 agent →
`843dcb0dbf4c` M4 embeddings/dupes/clarifications → `a2c5e1f09b34` embedding dim
1536 → `f1874a6ae1f5` users):

- **cities** — `id, name, slug (unique), timezone, config(jsonb)`, timestamps.
- **departments** — `id, city_id→cities, name, slug, category_tags[], contact_email`;
  unique `(city_id, slug)`.
- **users** — `id, city_id→cities, email (unique), full_name, hashed_password,
  role(user_role enum), is_active`, timestamps.
- **complaints** — `id, tracking_code (unique), city_id→cities, source
  (complaint_source), status (complaint_status), title, description,
  reporter_name, reporter_email, location_text, latitude, longitude, category,
  priority (complaint_priority), department_id→departments, resolved_at`,
  timestamps. Check constraint keeps `source` valid; indexes on
  `(city_id,status)` and `(city_id,source)`.
- **status_history** — append-only `id, complaint_id→complaints, from_status,
  to_status, actor, note, created_at`.
- **historical_311_requests** — dedicated Boston 311 table (case id, dates,
  category/dept/status, neighborhood, coords, etc.); never mutated by live flow.
- **agent_runs** — `id, complaint_id, graph_version, status (agent_run_status),
  llm_provider, llm_model, error, finished_at`, timestamps.
- **agent_steps** — per-node audit: `input/output(jsonb), confidence, latency_ms`.
- **agent_recommendations** — AI proposal + review state: proposed category/
  priority/department + confidences, `review_severity`, `status
  (recommendation_status)`, and the final human-approved values applied on review.
- **complaint_embeddings** — `complaint_id→complaints (unique), embedding
  vector(1536), provider, model, model_version, dim`; HNSW cosine index
  `ix_complaint_embeddings_hnsw` (hand-maintained, excluded from autogenerate).
- **duplicate_links** — `complaint_id, candidate_complaint_id, similarity,
  combined_score, evidence(jsonb), decision (duplicate_decision)`, reviewer/notes.
- **clarifications** — `complaint_id, agent_run_id?, field, question, answer,
  status (clarification_status)`.

Enums (`app/models/enums.py`): `ComplaintSource {web, 311_import}`,
`ComplaintStatus {submitted, triaged, in_progress, resolved, closed, rejected}`,
`ComplaintPriority {low, medium, high, urgent}`,
`AgentRunStatus {running, completed, needs_review, failed}`,
`RecommendationStatus {pending, approved, overridden, rejected}`,
`ReviewSeverity {routine, low_confidence, high_risk}`,
`DuplicateDecision {pending, confirmed, rejected}`,
`ClarificationStatus {pending, answered, dismissed}`,
`UserRole {staff, admin}`.

---

## 6. API endpoints

Base prefix `/api` for domain routes; health is unprefixed. Staff/admin routes
require a Bearer JWT (with a development-only unauthenticated fallback that is
never active in production).

Health: `GET /health`, `GET /health/ready`.

Auth (`/api/auth`): `POST /login`, `GET /me`, `POST /users` (admin only).

Cities (`/api/cities`): `GET ""`, `GET /{city_id}/departments`.

Complaints (`/api/complaints`):
- `POST ""` — submit (resident)
- `GET ""` — list live complaints (staff)
- `GET /track/{tracking_code}` — public, PII-free + timeline
- `GET /{complaint_id}` — staff detail
- `POST /{complaint_id}/status` — status transition (staff)
- `PATCH /{complaint_id}/assignment` — manual category/priority/department (staff)

Agent (`/api/agent`, admin-gated; triage is rate-limited):
- `POST /complaints/{complaint_id}/triage`
- `GET /runs/{run_id}`, `GET /runs`
- `GET /review-queue`
- `POST /recommendations/{recommendation_id}/decision` (approve/override/reject)

Duplicates (`/api/duplicates`, admin-gated; detect is rate-limited):
- `POST /complaints/{complaint_id}/detect`
- `GET /complaints/{complaint_id}/candidates`
- `POST /links/{link_id}/decision` (confirm/reject)
- `POST /complaints/{complaint_id}/clarifications/generate`
- `GET /complaints/{complaint_id}/clarifications`

Clarifications (`/api/clarifications`, public by tracking code):
- `GET /track/{tracking_code}`, `POST /{clarification_id}/answer`

Analytics (`/api/analytics`): `GET /overview`.

---

## 7. Frontend

Next.js App Router pages (`frontend/src/app/`): `/` (landing), `/submit`,
`/track`, `/login`, `/profile`, `/staff`, `/review`, `/analytics`.

Design system (`src/components/ui/`): Button, Card/StatCard, Field/Input/
Textarea/Select, Badge, Alert, Spinner, Skeleton, EmptyState, Container/
PageHeader, Icon (inline SVG). Shell: `AppShell` (responsive nav + theme toggle
+ auth-aware `UserMenu`). Theme tokens in `globals.css` (light primary + navy
dark via `.dark`), Inter font, `prefers-reduced-motion` respected.

API client: `src/lib/api.ts` — typed fetch wrapper; JWT stored in localStorage;
`getMe()` validates the session against `/auth/me`.

---

## 8. Verified project state

- Backend: **75 test functions** across `backend/tests/`. The suite runs against
  the Dockerized DB and forces offline fake providers (hermetic).
- Frontend: typecheck, `next build`, and `next lint` pass (verified during the
  UI/auth work).
- Embedding column is **vector(1536)**; default runtime providers are offline
  `fake` unless `LLM_PROVIDER`/`EMBEDDING_PROVIDER` + `LLM_API_KEY` are set.
- **Uncommitted working-tree changes** (auth-aware nav work, not yet committed):
  - modified: `frontend/src/components/AppShell.tsx`, `frontend/src/lib/api.ts`
  - new (untracked): `frontend/src/app/profile/`, `frontend/src/components/UserMenu.tsx`
- `.kiro/steering/` docs (product, tech, structure, development) exist and are
  tracked.

---

## 9. Known issues, bugs & UI notes

Behavioral / workflow (observed and documented during development):
- **Category unavailable at duplicate-detection time (ordering gap).** In the
  natural submit → detect → triage → review order, `complaint.category` is still
  null when duplicate detection runs (category is only written on review
  approval). So `_category_compatible` is neutral at detect time, and
  "same place, different issue type" pairs can only be separated by semantic +
  location signals. Re-running detection after review (or feeding the AI's
  proposed category into detection) would close this — a behavior change, not
  yet implemented.
- **Clarification answers are not folded back into the embedding.** A complaint
  is embedded once at submit from title+description; a resident's clarification
  reply is stored but never re-embedded, so it doesn't improve dedup/re-triage.
  Measured impact: a sparse complaint + detailed paraphrase sat at ~0.69 cosine
  (below threshold); with the clarified text it rose to ~0.72.
- **Duplicate threshold is a precision/recall tradeoff.** 0.78 with location-
  aware scoring cleanly separated an expanded real-embedding eval set, but the
  location-match boost only applies when semantic similarity is already near
  threshold, leaving a grey zone (~0.71–0.75) for same-street genuine duplicates
  without a category signal. Thresholds/weights are tuned on small synthetic
  sets — directional, not statistically validated.
- **Demo data is wiped by clean-slate migration checks.** Running a schema reset
  removes seeded users/complaints; re-run `python -m app.seed` / `python -m
  app.demo` to restore (the demo admin is `demo@civicroute.ai`).

Operational / non-functional:
- **Rate limiting is in-process** (single-instance) — not shared across workers;
  production needs a shared store (e.g. Redis).
- **Auth is minimal**: no refresh-token rotation, password reset, or login
  throttling/lockout. Dev-only unauthenticated admin fallback exists (disabled in
  production).
- **Real-model quality is not benchmarked at scale.** Evaluation ran on small
  synthetic sets and short real-model samples; accuracy/calibration/cost should
  be measured on a larger, ideally 311-derived, labeled set before relying on
  auto-confidence thresholds.

UI:
- The large UI modernization is committed (`f1bd2f9`); the auth-aware navigation
  is implemented but **uncommitted** (see §8).
- Historical status badges / charts rely on real backend data only; empty/error
  states are handled, but charts are intentionally simple (no chart library).
- Error surfaces are consistent (Alert component), but some staff flows reuse an
  info banner for transient status messages (e.g. triage result line).

No open compiler/lint/type errors were observed in the last verified runs.

---

## 10. Next development priorities

Suggested order, grounded in the gaps above:

1. **Commit the auth-aware navigation** work (currently uncommitted) after a
   final review.
2. **Close the duplicate-detection ordering gap** — make detection consider the
   AI's proposed (or approved) category, and/or re-embed + re-run detection after
   clarification answers are submitted. Add tests for the same-street /
   different-issue case.
3. **Fold clarification answers into the complaint context + re-embed**, so
   clarifications measurably improve dedup and re-triage.
4. **Larger, labeled evaluation** (ideally from Boston 311) to calibrate
   classification/priority/routing thresholds and duplicate thresholds on a real
   model; record accuracy, calibration, latency, and cost.
5. **Harden auth for production** — refresh tokens, password reset, login
   throttling; replace in-process rate limiting with a shared store; structured
   audit logging.
6. **Deployment** — containerize the backend, managed Postgres + pgvector, env/
   secret management, and observability (tracing, LLM cost dashboards).

Out of scope until explicitly requested: external notifications, real city-system
integrations, automatic duplicate merging.
