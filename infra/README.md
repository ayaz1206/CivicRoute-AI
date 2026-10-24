# Infra

Local infrastructure for CivicRoute AI.

## PostgreSQL + pgvector

```bash
docker compose up -d      # start
docker compose ps         # status
docker compose logs -f db # logs
docker compose down       # stop (keeps data)
docker compose down -v    # stop and DELETE data volume
```

- Image: `pgvector/pgvector:pg16` (PostgreSQL 16 with the `vector` extension bundled).
- Exposed on `localhost:5433` (host) → `5432` (container), configurable via `DB_HOST_PORT`.
- Credentials: `civicroute` / `civicroute`, database `civicroute`.
- `initdb/01-extensions.sql` runs on first boot and enables the `vector` extension.

Data persists in the `pgdata` Docker volume. The bind-mounted `pgdata/` directory is
git-ignored.
