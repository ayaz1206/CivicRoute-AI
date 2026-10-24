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

## Endpoints (M0)

| Method | Path            | Purpose                                   |
| ------ | --------------- | ----------------------------------------- |
| GET    | `/health`       | Liveness — process is up                  |
| GET    | `/health/ready` | Readiness — verifies DB connectivity      |

## Test

```bash
pytest
ruff check .
```
