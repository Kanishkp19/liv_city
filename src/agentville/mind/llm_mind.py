"""LLM mind: decide() through the gateway with schema-validated Proposals."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agentville.engine.types import AgentState, Proposal
from agentville.engine.world import World
from agentville.gateway.llm.base import InvalidModelOutput, LLMRequest, ProviderUnavailable
from agentville.gateway.llm.gateway import LLMGateway
from agentville.mind.briefing import build_briefing


class _ProposalSchema(BaseModel):
    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="", max_length=400)


class LLMMind:
    """decide() = briefing -> call_json(ProposalSchema); provider issues => noop."""

    def __init__(
        self,
        gateway: LLMGateway,
        *,
        observations: list[str] | None = None,
        notes: list[dict[str, Any]] | None = None,
        playbook: str | None = None,
        skills: list[str] | None = None,
    ) -> None:
        self.gw = gateway
        self.observations = observations or []
        self.notes = notes or []
        self.playbook = playbook
        self.skills = skills or []

    def decide(self, world: World, agent: AgentState) -> Proposal:
        """One decision; ProviderUnavailable/InvalidModelOutput become noop (no strike)."""
        b = build_briefing(world, agent, self.observations, self.notes, self.playbook, self.skills)
        req = LLMRequest(
            world_id=world.id, tick=world.tick, agent_id=agent.id,
            purpose="decide", system=b.system, user=b.user,
            temperature=0.7, max_tokens=400, json_mode=True, priority=1,
        )
        import asyncio

        try:
            out = asyncio.run(self.gw.call_json(req, _ProposalSchema))
        except (ProviderUnavailable, InvalidModelOutput, RuntimeError):
            return Proposal(action="noop", reason="provider unavailable")
        return Proposal(action=out.action, args=out.args, reason=out.reason)
