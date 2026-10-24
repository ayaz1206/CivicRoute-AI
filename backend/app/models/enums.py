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
