"""Domain enumerations for complaints.

These are stored as native PostgreSQL enums. Values are lowercase strings so
they are stable across the API and database.
"""

from __future__ import annotations

import enum


class ComplaintSource(str, enum.Enum):
    """Origin of a complaint record.

    ``WEB`` is a live resident submission flowing through the operational
    workflow. ``IMPORT_311`` is historical Boston 311 reference data, which is
    kept strictly separate from live complaints and is never produced by the
    resident submission path (enforced by a DB check constraint and the service
    layer). Historical import arrives in a later milestone.
    """

    WEB = "web"
    IMPORT_311 = "311_import"


class ComplaintStatus(str, enum.Enum):
    """Lifecycle of a live complaint (pre-agent, M1).

    Transitions in M1 are performed manually by staff. Agent-driven triage is
    added in a later milestone.
    """

    SUBMITTED = "submitted"
    TRIAGED = "triaged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"


class ComplaintPriority(str, enum.Enum):
    """Priority level. Nullable on the complaint until set by staff (M1) or the
    prioritization agent (later)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AgentRunStatus(str, enum.Enum):
    """Lifecycle of a single pass of a complaint through the agent graph."""

    RUNNING = "running"
    # Graph finished and the recommendation is confident enough to auto-apply
    # (still requires staff approval before touching the complaint).
    COMPLETED = "completed"
    # Graph finished but routed the recommendation to the human review queue.
    NEEDS_REVIEW = "needs_review"
    # Graph aborted due to an error (e.g. LLM provider failure).
    FAILED = "failed"


class RecommendationStatus(str, enum.Enum):
    """Review state of an AI recommendation.

    AI output is kept separate from final complaint data: a recommendation is
    only reflected on the complaint after a human APPROVES or OVERRIDES it.
    """

    PENDING = "pending"
    APPROVED = "approved"
    OVERRIDDEN = "overridden"
    REJECTED = "rejected"


class ReviewSeverity(str, enum.Enum):
    """How urgently a pending recommendation needs staff attention.

    ALL recommendations require mandatory staff approval before anything is
    applied to a complaint. This enum distinguishes recommendations that are
    merely *awaiting that routine approval* from those additionally *flagged*
    because the AI was uncertain (low confidence) or the case looks high-risk
    (e.g. urgent priority). The UI uses this to visually separate the two.
    """

    # Confident recommendation; just needs the mandatory human sign-off.
    ROUTINE = "routine"
    # AI confidence fell below threshold on one or more dimensions.
    LOW_CONFIDENCE = "low_confidence"
    # Case looks high-risk (urgent) or could not be routed/categorized.
    HIGH_RISK = "high_risk"
