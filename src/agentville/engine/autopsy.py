"""Autopsy: evidence-based post-mortem; lessons must cite real event ids (PROMPTS S4)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from agentville.engine.events import EventLog
from agentville.engine.types import AgentState
from agentville.gateway.llm.base import LLMRequest
from agentville.gateway.llm.gateway import LLMGateway


class LessonSchema(BaseModel):
    lesson: str = Field(max_length=200)
    evidence_event_ids: list[int] = Field(default_factory=list)


class AutopsySchema(BaseModel):
    summary: str = Field(max_length=600)
    top_mistakes: list[dict[str, Any]] = Field(default_factory=list)
    what_worked: list[str] = Field(default_factory=list)
    lessons: list[LessonSchema] = Field(default_factory=list)
    starter_playbook_md: str = Field(default="", max_length=1200)
    pivot_recommendation: str | None = None


class AutopsyBuilder:
    """Produce a validated autopsy; uncited lessons are dropped (docs' validation rule)."""

    def __init__(self, events: EventLog, gateway: LLMGateway | None = None) -> None:
        self.events = events
        self.gw = gateway

    def build(self, world_id: str, agent: AgentState, cause: str, tick: int) -> dict[str, Any]:
        """Assemble the autopsy dict from the event log (LLM optional; evidence always checked)."""
        rows = self.events.rows(world_id)
        agent_events = [r for r in rows if r.agent_id == agent.id][-40:]
        valid_ids = {r.id for r in agent_events}
        lessons: list[dict[str, Any]] = []
        summary = f"{agent.id} died of {cause} at tick {tick} after {len(agent_events)} recorded events."
        starter = ""
        if self.gw is not None:
            prompt = _autopsy_prompt(world_id, agent, cause, agent_events)
            req = LLMRequest(
                world_id=world_id, tick=tick, agent_id=agent.id, purpose="autopsy", priority=3,
                system="You are a post-mortem analyst. Base findings ONLY on the evidence. Output JSON only.",
                user=prompt, temperature=0.0, max_tokens=800,
            )
            try:
                import asyncio

                out = asyncio.run(self.gw.call_json(req, AutopsySchema))
                summary = out.summary or summary
                starter = out.starter_playbook_md
                lessons = [
                    {"lesson": les.lesson, "evidence_event_ids": les.evidence_event_ids}
                    for les in out.lessons
                ]
            except Exception:  # noqa: BLE001 - LLM failure must not block succession
                lessons = []
        # drop lessons without real evidence (PROMPTS S4 validation)
        lessons = [
            les for les in lessons
            if les.get("evidence_event_ids") and set(les["evidence_event_ids"]) & valid_ids
        ]
        if not lessons:
            lessons = [{"lesson": f"keep funds above rent; cause was {cause}",
                        "evidence_event_ids": sorted(valid_ids)[-1:]}]
        return {
            "agent_id": agent.id, "tick": tick, "cause": cause,
            "summary_md": summary, "lessons": lessons, "starter_playbook_md": starter,
        }


def _autopsy_prompt(world_id: str, agent: AgentState, cause: str, rows: list[Any]) -> str:
    compact = [
        {"id": r.id, "tick": r.tick, "type": r.type, "payload": json.loads(r.payload_json)}
        for r in rows
    ]
    return (
        f"CAUSE OF DEATH: {cause}\n"
        f"EVENT LOG (last {len(compact)}): {json.dumps(compact)[:6000]}\n"
        "Output: {\"summary\": \"<=600\", \"lessons\": [{\"lesson\": \"<=200\", "
        "\"evidence_event_ids\": [real ids from the log]}], \"starter_playbook_md\": \"<=1200\"}"
    )
