"""SQLAlchemy declarative base.

All ORM models (added in later milestones) will inherit from `Base`. Alembic's
autogenerate uses `Base.metadata` as the target schema.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
