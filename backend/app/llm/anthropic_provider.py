"""Anthropic Messages API adapter.

Uses httpx directly. Credentials come from the environment via settings. Any
failure (network, auth, non-JSON) raises LLMError.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.llm.base import LLMError

_API_URL = "https://api.anthropic.com/v1/messages"
_VERSION = "2023-06-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str | None = None, timeout: float = 30.0):
        if not api_key:
            raise LLMError("Anthropic provider requires LLM_API_KEY")
        self.api_key = api_key
        self.model = model or "claude-3-5-haiku-latest"
        self.timeout = timeout
        self.last_usage: dict[str, int] = {}

    async def complete_json(
        self, *, system: str, user: str, schema_hint: dict[str, Any]
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": 0,
            "system": system
            + " Respond ONLY with a single JSON object, no prose.",
            "messages": [
                {
                    "role": "user",
                    "content": f"{user}\n\nReturn JSON with keys: "
                    f"{list(schema_hint.keys())}.",
                }
            ],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": _VERSION,
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http:
                resp = await http.post(_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["content"][0]["text"]
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        usage = data.get("usage") or {}
        in_tok = int(usage.get("input_tokens", 0))
        out_tok = int(usage.get("output_tokens", 0))
        self.last_usage = {
            "prompt_tokens": in_tok,
            "completion_tokens": out_tok,
            "total_tokens": in_tok + out_tok,
        }

        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LLMError(f"Anthropic returned non-JSON output: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LLMError("Anthropic returned JSON that is not an object")
        return parsed
