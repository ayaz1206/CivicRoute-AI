"""ORM models for CivicRoute AI.

Importing this package registers all models on ``Base.metadata`` so that
Alembic autogenerate and ``create_all`` can see them.
"""

from app.models.agent import AgentRecommendation, AgentRun, AgentStep
from app.models.city import City
from app.models.complaint import Complaint
from app.models.department import Department
from app.models.duplicate import Clarification, ComplaintEmbedding, DuplicateLink
from app.models.enums import (
    AgentRunStatus,
    ClarificationStatus,
    ComplaintPriority,
    ComplaintSource,
    ComplaintStatus,
    DuplicateDecision,
    RecommendationStatus,
    ReviewSeverity,
    UserRole,
)
from app.models.historical_request import Historical311Request
from app.models.status_history import StatusHistory
from app.models.user import User

__all__ = [
    "City",
    "Department",
    "Complaint",
    "StatusHistory",
    "Historical311Request",
    "AgentRun",
    "AgentStep",
    "AgentRecommendation",
    "ComplaintEmbedding",
    "DuplicateLink",
    "Clarification",
    "User",
    "ComplaintSource",
    "ComplaintStatus",
    "ComplaintPriority",
    "AgentRunStatus",
    "RecommendationStatus",
    "ReviewSeverity",
    "DuplicateDecision",
    "ClarificationStatus",
    "UserRole",
]
