# CivicRoute AI

An Agentic AI-powered smart city complaint management platform. CivicRoute AI lets
residents submit complaints, then uses an agentic workflow to classify, clarify,
detect duplicates, score risk, and route each complaint to the right department —
with human review and auditable AI decision logs throughout.

> **Status:** M1 — Core Complaint Management. Residents can submit and track
> complaints; staff can review and manage them through a validated status
> lifecycle. AI agents, authentication, and historical 311 ingestion are
> intentionally **not** implemented yet.

## Tech Stack

| Layer      | Technology                                             |
| ---------- | ------------------------------------------------------ |
| Frontend   | Next.js (App Router), TypeScript, Tailwind CSS         |
| Backend    | Python, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2   |
| Database   | PostgreSQL 16 + `pgvector`                             |
| Migrations | Alembic                                                |
| Agents     | LangGraph (later milestone)                            |
| LLM        | Configurable provider (later milestone)                |

## Architecture (high level)

```
Next.js (resident + admin UIs)
        │  HTTPS / REST
FastAPI (API + domain services)
        │
PostgreSQL + pgvector  ◄── Alembic migrations
```

Design principles established in M0 and carried forward:

- **Multi-city (multi-tenant):** every domain row is scoped by `city_id`. Boston is the first city.
- **Historical data is separate from live complaints:** imported 311 records are read-only
  reference data and never flow through the live complaint workflow.
- **Human-controlled duplicate merging:** the AI will only ever *flag* duplicate candidates;
  merging is always a human action.
- **Auditable AI decisions:** agent runs and steps are persisted for explainability and audit.

## Repository Layout

```
CivicRoute-AI/
├── backend/            # FastAPI application
│   ├── app/
│   │   ├── core/       # config, settings
│   │   ├── db/         # engine, session, base
│   │   ├── api/        # routers (health in M0)
│   │   └── main.py     # app factory
│   ├── alembic/        # migrations
│   ├── tests/          # pytest suite
│   └── pyproject.toml
├── frontend/           # Next.js application
├── infra/              # docker-compose for Postgres + pgvector
├── docs/               # architecture & setup docs
└── README.md
```

## Quick Start

See [docs/SETUP.md](docs/SETUP.md) for full instructions. In short:

```bash
# 1. Start Postgres + pgvector
cd infra && docker compose up -d

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

# 3. Frontend
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Backend health check: http://localhost:8000/health
Frontend: http://localhost:3000

## Documentation

- [docs/SETUP.md](docs/SETUP.md) — environment setup and running locally
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — architecture, entities, and roadmap

## Milestones

- **M0 — Foundation**: monorepo, FastAPI + Next.js skeletons, Postgres+pgvector,
  Alembic, config, health checks, tests, docs.
- **M1 — Core complaint management** *(current)*: complaint domain models
  (cities, departments, complaints, status history), complaint CRUD API with
  validated status transitions, resident submission + tracking pages, staff
  dashboard, and tests. Historical 311 data is kept separate from live complaints.
- M2 — Agentic core (LangGraph)
- M3 — Semantic intelligence + Boston 311 ingestion
- M4 — Human review + admin analytics
- M5 — Evaluation & polish
