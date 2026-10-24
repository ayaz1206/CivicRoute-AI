"""ORM models for CivicRoute AI.

Importing this package registers all models on ``Base.metadata`` so that
Alembic autogenerate and ``create_all`` can see them.
"""

from app.models.city import City
from app.models.complaint import Complaint
from app.models.department import Department
from app.models.enums import (
    ComplaintPriority,
    ComplaintSource,
    ComplaintStatus,
)
from app.models.historical_request import Historical311Request
from app.models.status_history import StatusHistory

__all__ = [
    "City",
    "Department",
    "Complaint",
    "StatusHistory",
    "Historical311Request",
    "ComplaintSource",
    "ComplaintStatus",
    "ComplaintPriority",
]
