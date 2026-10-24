"""Configurable LLM provider abstraction (M3).

A single small interface (`LLMProvider.complete_json`) is used by the agent
nodes. Adapters are selected via settings (`LLM_PROVIDER`) with credentials from
the environment. A deterministic ``fake`` provider lets the full agent workflow
run offline and makes tests hermetic.
"""

from app.llm.base import LLMError, LLMProvider
from app.llm.factory import get_llm_provider

__all__ = ["LLMProvider", "LLMError", "get_llm_provider"]
