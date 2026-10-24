# Structure — Repository Layout

Top level:

```
CivicRoute-AI/
├── backend/      # FastAPI application, agents, migrations, tests
├── frontend/     # Next.js (App Router) resident + staff UI
├── infra/        # docker-compose for PostgreSQL + pgvector
├── docs/         # ARCHITECTURE.md, SETUP.md, DEMO.md
├── .kiro/        # steering docs (this directory)
└── README.md
```

## backend/

```
backend/
├── app/
│   ├── main.py            # create_app(): FastAPI factory, router + error wiring
│   ├── seed.py            # seed Boston city + departments (+ optional admin)
│   ├── demo.py            # seed a reproducible end-to-end demo scenario
│   ├── core/              # config (pydantic-settings), security (JWT/bcrypt),
│   │                      #   rate limiting
│   ├── db/                # async engine, session, declarative Base
│   ├── models/            # SQLAlchemy ORM entities + enums
│   ├── schemas/           # Pydantic request/response models
│   ├── api/               # routers: health, auth, cities, complaints,
│   │                      #   agent, duplicates, analytics (+ deps/auth_deps)
│   ├── services/          # business logic (see below)
│   ├── agent/             # LangGraph graph, nodes, routing, categories,
│   │                      #   clarification, evaluation dataset
│   ├── llm/               # LLM provider protocol, factory, fake/openai/
│   │                      #   anthropic adapters, retry/timeout helper
│   ├── embeddings/        # embedding provider protocol, factory, fake/openai,
│   │                      #   safe re-embedding tool
│   ├── eval/              # evaluation + duplicate-pair + e2e demo harnesses
│   └── ingestion/         # Boston 311 CKAN client, parser, ingest service/CLI
├── alembic/               # migration env + versioned migrations
├── tests/                 # pytest suite
├── pyproject.toml         # deps + ruff/pytest config
└── .env.example           # documented settings (no secrets)
```

### Component responsibilities

Models (`app/models/`):
- `city`, `department`, `user` — tenant root, routing targets, staff accounts.
- `complaint`, `status_history` — the central live entity and its timeline.
- `historical_request` (`Historical311Request`) — dedicated Boston 311 table,
  physically separate from live complaints.
- `agent` — `AgentRun` / `AgentStep` / `AgentRecommendation` (auditable AI
  output, separate from the complaint).
- `duplicate` — `ComplaintEmbedding` (pgvector), `DuplicateLink`
  (human-confirmed), `Clarification` (Q&A).
- `enums` — complaint status/priority/source, agent run status, recommendation
  status, review severity, duplicate decision, clarification status, user role.

Services (`app/services/`):
- `complaint_service` — create/list/get, status transitions, best-effort
  embedding on submit.
- `agent_service` — runs the triage graph and persists runs/steps/recommendations.
- `review_service` — the single place a human approve/override applies AI values
  to a complaint.
- `duplicate_service` — embedding, pgvector KNN, combined scoring, human
  confirm/reject.
- `clarification_service` — generate and resolve clarification questions.
- `analytics_service` — aggregates over the historical 311 table.
- `auth_service`, `city_service` — authentication and city/department reads.

API (`app/api/`):
- `deps.py` / `auth_deps.py` — dependency injection, role guards
  (`require_admin`, `require_roles`), dev-only unauthenticated fallback.
- Routers map HTTP to services; expensive AI endpoints carry a rate-limit guard.

## frontend/

```
frontend/src/
├── app/                   # App Router pages
│   ├── page.tsx           # home / landing
│   ├── submit/            # resident complaint submission
│   ├── track/             # resident tracking + clarification answers
│   ├── staff/             # staff dashboard (list, detail, triage, duplicates)
│   ├── review/            # AI recommendation review queue
│   ├── analytics/         # Boston 311 analytics dashboard
│   ├── login/             # staff sign-in
│   ├── layout.tsx         # shell + NavBar
│   └── globals.css        # Tailwind + theme variables (light/dark)
├── components/            # NavBar, AuthLink, StatusBadge, SeverityBadge,
│                          #   Timeline, ConfidenceBar, BarChart, TrendChart
└── lib/api.ts             # typed API client + token storage
```

## infra/

`docker-compose.yml` runs PostgreSQL 16 + pgvector; `initdb/` enables the
`vector` extension; `backups/` (git-ignored) holds ad-hoc data backups.

## Migrations (`backend/alembic/versions/`)

Chained migrations build the schema incrementally: core complaint schema →
historical 311 table → agent decision tables → embeddings/duplicates/
clarifications → users → 1536-dim embedding column. `alembic/env.py` sources the
DB URL and metadata from the app so there is one source of truth.
