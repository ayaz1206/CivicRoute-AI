"""baseline

Establishes the migration chain for CivicRoute AI and ensures the pgvector
extension is available so later migrations can define vector columns. No domain
tables are created in M0 — those arrive in M1+.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-24

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Idempotent: the Docker init script also creates this, but running it here
    # keeps migrations self-sufficient on any database.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Leave the extension in place on downgrade; dropping it could affect other
    # schemas. Baseline has no tables to remove.
    pass
