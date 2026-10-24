# Alembic Migrations

```bash
alembic upgrade head          # apply all migrations
alembic revision -m "msg"     # create an empty migration
alembic revision --autogenerate -m "msg"   # diff models vs. DB (needs models)
alembic downgrade -1          # roll back one revision
alembic current               # show current revision
```

The database URL and target metadata are sourced from the application
(`app.core.config` and `app.db.base`) in `env.py`, so there is a single source of
truth. Import new ORM models in `env.py` as they are added so autogenerate can see
them.

## M0 baseline

`versions/0001_baseline.py` is an empty baseline. It establishes the migration
chain and enables the `vector` extension (idempotently) so later migrations can
define `vector` columns. Domain tables arrive in M1+.
