"""OpenAI chat-completions adapter (JSON mode).

Uses httpx directly to avoid a heavy SDK dependency. Credentials come from the
environment via settings. Any failure (network, auth, non-JSON) raises LLMError.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.llm.base import LLMError
from app.llm.http import post_with_retries

_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str | None = None, timeout: float = 30.0):
        if not api_key:
            raise LLMError("OpenAI provider requires LLM_API_KEY")
        settings = get_settings()
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"
        self.timeout = settings.llm_timeout_seconds or timeout
        self.max_tokens = settings.llm_max_output_tokens
        self.max_retries = settings.llm_max_retries
        # Populated after each call for cost/telemetry (never contains secrets).
        self.last_usage: dict[str, int] = {}

    async def complete_json(
        self, *, system: str, user: str, schema_hint: dict[str, Any]
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"{user}\n\nReturn JSON with keys: "
                    f"{list(schema_hint.keys())}.",
                },
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = await post_with_retries(
            _API_URL, payload, headers, self.timeout, self.max_retries
        )
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"OpenAI response malformed: {exc}") from exc

        usage = data.get("usage") or {}
        self.last_usage = {
            "prompt_tokens": int(usage.get("prompt_tokens", 0)),
            "completion_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)),
        }

        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LLMError(f"OpenAI returned non-JSON output: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LLMError("OpenAI returned JSON that is not an object")
        return parsed
