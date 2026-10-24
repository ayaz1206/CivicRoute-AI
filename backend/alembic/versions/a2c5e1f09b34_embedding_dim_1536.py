"""Change complaint_embeddings.embedding from vector(384) to vector(1536).

Context: switching the embedding provider to OpenAI text-embedding-3-small,
which produces 1536-dimensional vectors. Existing 384-d vectors live in a
different (incompatible) vector space and cannot be cast or reused, so they are
removed here and REGENERATED afterwards by `python -m app.embeddings.reembed`.

Safety:
- Only the ``complaint_embeddings`` rows are deleted — complaints, historical
  311 records, agent decisions, clarifications, duplicate links, and staff data
  are all untouched.
- A backup of the table was taken before running this migration (see
  infra/backups/ and the complaint_embeddings_backup_* table).
- ``downgrade`` restores the 384-d column + index (also empty; re-embed with the
  previous provider to repopulate).

Revision ID: a2c5e1f09b34
Revises: f1874a6ae1f5
Create Date: 2026-10-24

"""
from __future__ import annotations

from collections.abc import Sequence

import pgvector.sqlalchemy
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2c5e1f09b34"
down_revision: str | None = "f1874a6ae1f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_HNSW = "ix_complaint_embeddings_hnsw"


def upgrade() -> None:
    # 1. Drop the HNSW index (tied to the 384-d column).
    op.drop_index(_HNSW, table_name="complaint_embeddings")

    # 2. Remove incompatible 384-d vectors. They cannot be converted to the new
    #    space; embeddings are regenerated post-migration. Complaints are kept.
    op.execute("DELETE FROM complaint_embeddings")

    # 3. Widen the column to 1536 dimensions. The table is now empty so there is
    #    no row to fail the cast; USING keeps the statement explicit.
    op.alter_column(
        "complaint_embeddings",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(384),
        type_=pgvector.sqlalchemy.Vector(1536),
        existing_nullable=False,
        postgresql_using="embedding::vector(1536)",
    )

    # 4. Recreate the HNSW cosine index on the new column.
    op.create_index(
        _HNSW,
        "complaint_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index(_HNSW, table_name="complaint_embeddings")
    op.execute("DELETE FROM complaint_embeddings")
    op.alter_column(
        "complaint_embeddings",
        "embedding",
        existing_type=pgvector.sqlalchemy.Vector(1536),
        type_=pgvector.sqlalchemy.Vector(384),
        existing_nullable=False,
        postgresql_using="embedding::vector(384)",
    )
    op.create_index(
        _HNSW,
        "complaint_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
