"""Build the LangGraph triage workflow.

Linear pipeline with an error short-circuit:

    extract -> classify -> prioritize -> route -> gate -> END

If any node sets ``error`` on the state, subsequent nodes no-op (they check the
error flag) and the gate marks the recommendation for review. Human review is
handled out-of-band by the review service/API rather than a live interrupt, so
the graph stays a pure request/response unit of work suitable for a web backend.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.nodes import TriageNodes
from app.agent.state import TriageState
from app.llm.base import LLMProvider

GRAPH_VERSION = "v1"


def build_triage_graph(llm: LLMProvider, session: AsyncSession):
    """Compile and return the triage graph."""
    nodes = TriageNodes(llm, session)

    graph = StateGraph(TriageState)
    graph.add_node("extract", nodes.extract)
    graph.add_node("classify", nodes.classify)
    graph.add_node("prioritize", nodes.prioritize)
    graph.add_node("route", nodes.route)
    graph.add_node("gate", nodes.gate)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "classify")
    graph.add_edge("classify", "prioritize")
    graph.add_edge("prioritize", "route")
    graph.add_edge("route", "gate")
    graph.add_edge("gate", END)

    return graph.compile()
