# Product — CivicRoute AI

## Purpose

CivicRoute AI is an agentic, AI-assisted complaint management platform for city
governments. Residents report non-emergency issues (potholes, broken street
lights, overflowing trash, graffiti, etc.); the system uses an LLM-driven
workflow to extract structured details, classify the issue, recommend a
priority, and route it to the responsible department. Every AI output is a
recommendation that a staff member must approve before it is applied — AI never
makes a final, binding change on its own.

The project is designed to be multi-city (tenant-scoped by `city_id`), with
Boston as the first supported city. Historical Boston 311 Open Data is used as
reference/analytics data and is kept strictly separate from live resident
complaints.

## Target users

- **Residents** — submit complaints anonymously (no account), answer
  clarification questions, and track status by a tracking code.
- **City staff / administrators** — authenticated users who review AI
  recommendations, approve/override/reject them, manage complaint status,
  confirm or dismiss possible duplicates, and view analytics. `admin` can also
  create staff accounts.

## Implemented features

Resident-facing:
- Complaint submission with title, description, optional location text and
  coordinates, and optional reporter contact.
- Public tracking by tracking code, showing status, a status timeline, and a
  PII-free view (reporter name/email are never exposed on the public endpoint).
- Interactive clarification: residents answer targeted follow-up questions when
  information (e.g. location) is missing; answers persist and resume the flow.

AI / agentic workflow (LangGraph):
- A triage graph: extract → classify → prioritize → route → gate. It produces a
  confidence-scored, auditable recommendation (classification, priority with a
  rationale, and a Boston department derived from a validated mapping plus
  historical 311 patterns).
- Priority uses an explicit four-level rubric (low / medium / high / urgent)
  with urgent reserved for immediate safety threats.
- A review-gating step flags low-confidence or high-risk cases
  (`review_severity`: routine / low_confidence / high_risk).
- Configurable LLM provider (a deterministic offline "fake" default, plus
  OpenAI and Anthropic adapters); credentials come from the environment.

Duplicate detection:
- Semantic similarity search over live complaints using PostgreSQL + pgvector,
  blended with category compatibility and location evidence (coordinates when
  available, normalized location-text comparison otherwise). Missing locations
  are treated as unknown, never as a mismatch.
- Produces a ranked list of possible duplicates with evidence. Duplicate
  confirmation is always a human action; complaints are never auto-merged.

Staff / admin:
- Authentication (JWT) with `staff` and `admin` roles; role-based access
  control on administrative endpoints.
- Staff dashboard: list/filter live complaints, inspect details (assigned
  fields vs. pending AI recommendation), run triage and duplicate detection,
  manage status transitions, and confirm/reject duplicates.
- AI review queue separating flagged (high-risk / low-confidence) from routine
  recommendations awaiting approval.
- Boston 311 analytics dashboard: totals, category / neighborhood / department /
  status breakdowns, and a daily trend, over the historical 311 dataset.

Data & evaluation:
- Idempotent ingestion of Boston 311 Open Data into a dedicated historical table.
- An evaluation harness measuring classification/priority/routing accuracy,
  confidence calibration, latency, and (for real providers) token cost, plus a
  duplicate-pair evaluation.

## Explicitly NOT implemented

To set honest expectations: there are no external notifications (email/SMS), no
integrations with real Boston city systems, and no automatic duplicate merging.
These are intentionally out of scope.
