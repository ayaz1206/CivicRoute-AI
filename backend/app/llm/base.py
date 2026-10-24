"""LLM provider protocol and shared errors."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class LLMError(Exception):
    """Raised when an LLM call fails (network, auth, timeout, bad output).

    Agent nodes catch this and fail the run gracefully rather than crashing.
    """


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal interface the agent depends on.

    Implementations must return a parsed JSON object (dict). They are
    responsible for prompting the model to emit JSON and for parsing it;
    on any failure they must raise :class:`LLMError`.
    """

    name: str
    model: str | None

    async def complete_json(
        self, *, system: str, user: str, schema_hint: dict[str, Any]
    ) -> dict[str, Any]:
        """Return a parsed JSON object for the given prompt.

        ``schema_hint`` documents the expected keys so the prompt can instruct
        the model; implementations may also use it to validate/repair output.
        """
        ...
