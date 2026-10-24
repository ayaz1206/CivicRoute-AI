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

## Seed reference data

```bash
python -m app.seed   # creates Boston + departments (no complaints, no 311 data)
```

## Test

```bash
pytest
ruff check .
```
