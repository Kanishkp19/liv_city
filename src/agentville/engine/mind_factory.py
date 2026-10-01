"""Mind factory: builds per-agent minds for mock or live LLM modes."""

from __future__ import annotations

from typing import Any


def build_minds(
    agents: dict[str, Any] | Any,
    session: Any,
    *,
    mode: str = "mock",
    mock_policy: str = "oracle",
) -> dict[str, Any]:
    """Map agent_id -> mind; mode 'llm' routes decisions through the gateway."""
    agents_map = agents if isinstance(agents, dict) else {a.id: a for a in agents}
    if mode == "mock":
        from agentville.engine.mocks import MockMind

        return {aid: MockMind(mock_policy) for aid in agents_map}
    if mode == "llm":
        from agentville.gateway.llm.gateway import LLMGateway
        from agentville.mind.llm_mind import LLMMind

        gw = LLMGateway(session)
        return {aid: LLMMind(gw) for aid in agents_map}
    msg = f"unknown mind mode: {mode} (expected mock|llm)"
    raise ValueError(msg)
