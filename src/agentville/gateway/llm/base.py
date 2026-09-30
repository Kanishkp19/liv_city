"""LLM gateway core: request/response models, Provider protocol, errors (LLM_GATEWAY S1-S2)."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel

Purpose = Literal["decide", "produce_artifact", "judge", "autopsy", "summarize_notes", "exam"]


class LLMRequest(BaseModel):
    world_id: str
    tick: int
    agent_id: str | None = None
    purpose: str
    call_index: int = 0
    system: str
    user: str
    temperature: float = 0.7
    max_tokens: int = 400
    json_mode: bool = True
    priority: int = 1  # 0 highest (LLM_GATEWAY S3)
    model_hint: str | None = None


class LLMResponse(BaseModel):
    text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    cached: bool = False
    repaired: bool = False


class ProviderUnavailable(Exception):
    """All providers failed; engine skips the agent as noop (no strike)."""


class InvalidModelOutput(Exception):
    """Structured parse failed even after repair."""


class ReplayMiss(Exception):
    """Replay mode missing a recorded response -> halt, never a silent live call."""


class Provider(Protocol):
    """Provider adapter contract; SDKs never leave providers/ (AGENTS rule 8)."""

    id: str
    model: str

    async def complete(self, req: LLMRequest) -> LLMResponse:  # pragma: no cover
        ...


def redact(text: str) -> str:
    """Strip key-like strings from prompt/log paths (LLM_GATEWAY S10)."""
    import re

    patterns = [
        r"(sk|pk|rk)-[A-Za-z0-9_-]{16,}",
        r"(?i)api[_-]?key[\"']?\s*[:=]\s*[\"'][^\"']{8,}[\"']",
        r"(?i)bearer\s+[A-Za-z0-9._-]{16,}",
        r"ghp_[A-Za-z0-9]{30,}",
    ]
    out = text
    for p in patterns:
        out = re.sub(p, "[REDACTED]", out)
    return out
