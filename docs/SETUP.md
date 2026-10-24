# Setup Guide

This guide covers running CivicRoute AI locally for the **M0 — Foundation** milestone.

## Prerequisites

- Python 3.11+ (developed on 3.13)
- Node.js 20+ (developed on 24)
- Docker + Docker Compose (for PostgreSQL + pgvector)

You do **not** need a local PostgreSQL server — the database runs in Docker.

## 1. Database (PostgreSQL + pgvector)

The database runs via Docker Compose using the official `pgvector/pgvector` image,
which bundles PostgreSQL 16 with the `vector` extension.

```bash
cd infra
docker compose up -d
```

This starts Postgres on `localhost:5432` with:

- user: `civicroute`
- password: `civicroute`
- database: `civicroute`

> **Port note:** the container listens on 5432 internally but is published on host
> port **5433** by default (set via `DB_HOST_PORT`) to avoid colliding with any other
> local Postgres on 5432. Override with `DB_HOST_PORT=5555 docker compose up -d` and
> update `DATABASE_URL` to match.

The `vector` extension is created automatically on first boot via
`infra/initdb/01-extensions.sql`.

To stop: `docker compose down`. To wipe data: `docker compose down -v`.

## 2. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env              # defaults match the Docker DB above
```

Run migrations and start the server:

```bash
alembic upgrade head
python -m app.seed              # seed Boston + departments (reference data only)
uvicorn app.main:app --reload
```

- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Readiness (checks DB): http://localhost:8000/health/ready

Run the tests:

```bash
pytest
```

## 3. Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local  # points at the backend above
npm run dev
```

Visit http://localhost:3000. The home page shows live backend health status.

## Environment Variables

### Backend (`backend/.env`)

| Variable        | Default                                                        | Purpose                     |
| --------------- | ------------------------------------------------------------- | --------------------------- |
| `DATABASE_URL`  | `postgresql+asyncpg://civicroute:civicroute@localhost:5433/civicroute` | Async DB connection |
| `APP_ENV`       | `development`                                                 | Environment name            |
| `API_PREFIX`    | `/api`                                                        | Prefix for versioned routes |
| `CORS_ORIGINS`  | `http://localhost:3000`                                       | Allowed frontend origins    |

### Frontend (`frontend/.env.local`)

| Variable               | Default                 | Purpose              |
| ---------------------- | ----------------------- | -------------------- |
| `NEXT_PUBLIC_API_URL`  | `http://localhost:8000` | Backend base URL     |

## Troubleshooting

- **`alembic upgrade head` fails to connect:** ensure Docker DB is up (`docker compose ps`).
- **Port 5432 in use:** the DB is published on host port **5433** by default. If 5433 is
  also taken, set `DB_HOST_PORT` to a free port and update `DATABASE_URL` to match.
- **pgvector errors:** confirm you are using the `pgvector/pgvector` image, not plain `postgres`.
