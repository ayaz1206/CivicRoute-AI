# Architecture

This document records the approved architecture for CivicRoute AI. M0 implements only
the foundation; later sections describe the intended end state and are built incrementally.

## Principles

1. **Multi-city (multi-tenant).** Every domain entity is scoped by `city_id`.
   Boston is the first city; the schema supports many.
2. **Historical data is separated from live complaints.** Imported Boston 311 records are
   read-only reference data used for patterns and evaluation. They never enter the live
   complaint workflow and are distinguished by a `source` discriminator.
3. **Duplicate merging stays under human control.** The agentic layer will only *flag*
   duplicate candidates; a human performs any merge.
4. **AI decisions are auditable.** Agent runs and per-step inputs/outputs are persisted so
   every automated decision can be explained and reviewed.

## Components

| Component        | Responsibility                                                        |
| ---------------- | --------------------------------------------------------------------- |
| Frontend         | Resident submission/tracking + admin/staff dashboards (Next.js)       |
| API              | REST endpoints, validation, tenant scoping, orchestration (FastAPI)   |
| Domain services  | Complaint, routing, analytics, user logic                             |
| Agent orchestrator | LangGraph state machine (M2+)                                       |
| LLM provider     | Configurable adapter: classify / embed / complete (M2+)               |
| Database         | PostgreSQL + pgvector, accessed via async SQLAlchemy                  |
| Data/ETL         | Boston 311 ingestion + embedding backfill (M3+)                       |

## Data Model (target)

M0 ships migration scaffolding and the DB layer, not the full schema. The target
entity set (built out in M1–M4):

- `cities` — tenant root (name, slug, timezone, config).
- `departments` — routing targets, scoped by city.
- `users` — residents/staff/admins, scoped by city.
- `complaints` — central entity; carries `source` (`web` vs `311_import`), status,
  category, priority, risk_score, department, and a nullable `duplicate_of_id` link.
- `complaint_embeddings` — pgvector store, kept separate so re-embedding is clean.
- `agent_runs` / `agent_steps` — auditable AI decision trail.
- `clarifications` — AI questions + resident answers.
- `reviews` — human-in-the-loop decisions (including duplicate merge approvals).
- `status_history` — resident-facing tracking timeline.
- `audit_log` — security/compliance trail.

### Live vs. historical separation

`complaints.source` discriminates origin. Historical 311 imports are flagged distinctly
and excluded from live operational queries by default. Duplicate *detection* may compare a
live complaint against historical patterns, but historical rows are never mutated by the
live workflow and never auto-merged.

## Agent Workflow (target, M2+)

`INTAKE → CLASSIFY → (CLARIFY loop) → DEDUPLICATE(flag only) → PRIORITIZE → ROUTE → (HUMAN REVIEW) → FINALIZE`

CLARIFY and HUMAN REVIEW are LangGraph interrupt points. Low-confidence outcomes route to
human review rather than auto-acting.

## Roadmap

- **M0 — Foundation** *(current)*: skeletons, DB, migrations, config, health checks, tests, docs.
- **M1** — Core complaint loop (CRUD, submission, tracking, auth, RBAC, tenant scoping).
- **M2** — Agentic core (LangGraph intake→classify→route, agent-run persistence).
- **M3** — Semantic intelligence (embeddings, pgvector dedup flagging, Boston 311 ETL).
- **M4** — Human review + admin analytics + audit logging.
- **M5** — Evaluation & polish (accuracy harness vs. 311 labels, demo seed, hardening).
