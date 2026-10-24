"""LangGraph agentic core (M3).

A deterministic, auditable workflow that triages a newly submitted resident
complaint:

    extract -> classify -> prioritize -> route -> gate

The graph produces an AgentRecommendation (kept separate from the complaint) and
either marks it ready or routes it to the human review queue. It performs NO
semantic duplicate detection, embeddings, notifications, or external
integrations.
"""

from app.agent.categories import SUPPORTED_CATEGORIES

__all__ = ["SUPPORTED_CATEGORIES"]
