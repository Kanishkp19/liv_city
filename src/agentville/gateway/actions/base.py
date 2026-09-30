"""Action gateway primitives: ActionSpec, Handler protocol, ActionContext (TRD S3.6/S3.7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel

from agentville.engine.events import EventLog
from agentville.engine.ledger import LedgerWriter
from agentville.engine.types import ActionResult, AgentState
from agentville.engine.world import World


class ActionSpec(BaseModel):
    """Static definition of one action: energy cost model and arg schema."""

    name: str
    arg_schema: type[BaseModel]
    energy_cost: int = 0
    energy_per_effort: int = 0
    coin_cost: int = 0
    roles: list[str] | None = None  # None = all roles
    description: str = ""


class Handler(Protocol):
    """One handler per action; validate + execute, no DB writes outside gateway."""

    spec: ActionSpec

    def validate(self, ctx: ActionContext, args: BaseModel) -> None:
        """Raise PreconditionFailed (no strike) or ValidationError (strike) on bad input."""
        ...

    def execute(self, ctx: ActionContext, args: BaseModel) -> ActionResult:
        """Apply the action; returns result with observation for next briefing."""
        ...


@dataclass
class ActionContext:
    """Everything a handler may touch; constructed by the gateway per call."""

    world: World
    agent: AgentState
    ledger: LedgerWriter
    events: EventLog
    tick: int
    llm_call_id: int | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class ValidationError(Exception):
    """Agent-fault rejection: counts a strike (TRD S9)."""


class PreconditionFailed(Exception):
    """Legitimate failed attempt: no strike (TRD S9)."""


class IdempotencyError(Exception):
    """Duplicate (agent, tick, action, args) proposal."""
