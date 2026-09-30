"""RemoteProvider: OpenAI-compatible HTTP via httpx (freellmapi + ollama kinds)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from agentville.gateway.llm.base import LLMRequest, LLMResponse


class RemoteProvider:
    """Talks to FREELLMAPI_URL or OLLAMA_URL with the chat/completions shape."""

    def __init__(self, cfg: Any) -> None:
        self.id = cfg.id
        self.model = cfg.model
        self.kind = cfg.kind
        if cfg.kind == "ollama":
            self.base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/v1"
            self.api_key = "ollama"
        else:
            self.base_url = os.environ.get("FREELLMAPI_URL", "http://localhost:3001/v1")
            self.api_key = os.environ.get("FREELLMAPI_KEY", "")

    async def complete(self, req: LLMRequest) -> LLMResponse:
        """POST /chat/completions; raises on HTTP errors (gateway handles failover)."""
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": req.system},
                {"role": "user", "content": req.user},
            ],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.json_mode:
            payload["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            if r.status_code == 429:
                retry_after = float(r.headers.get("Retry-After", "5"))
                raise RuntimeError(f"429 rate limited (retry_after={retry_after})")
            if r.status_code == 404:
                raise RuntimeError("404 model not found")
            r.raise_for_status()
            data = r.json()
        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        return LLMResponse(
            text=text, provider=self.id, model=self.model,
            tokens_in=int(usage.get("prompt_tokens", 0)),
            tokens_out=int(usage.get("completion_tokens", 0)),
        )
