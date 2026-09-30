"""Action gateway: validate proposals and execute handlers (TRD S3.6)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import ValidationError as PydValidationError

from agentville.engine.events import EventLog
from agentville.engine.jobs import JobBoard, JobStatus
from agentville.engine.ledger import LedgerWriter
from agentville.engine.types import ActionResult, AgentState, Proposal
from agentville.engine.world import World
from agentville.gateway.actions.base import (
    ActionContext,
    IdempotencyError,
    PreconditionFailed,
    ValidationError,
)


def idempotency_key(agent_id: str, tick: int, action: str, args: dict[str, Any]) -> str:
    """sha256(agent, tick, action, canonical args) per TRD S3.6 step 6."""
    body = json.dumps(
        {"a": agent_id, "t": tick, "act": action, "args": args},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def validate_and_build(
    world: World,
    agent: AgentState,
    proposal: Proposal,
    seen_keys: set[str],
) -> tuple[Any, Any]:
    """Steps 1-6; returns (spec, args_model) or raises with reject reason.

    Raises ValidationError for agent faults (strike), PreconditionFailed otherwise.
    """
    # (1) action exists
    from agentville.gateway.actions.registry import get_spec

    spec = get_spec(proposal.action)
    if spec is None:
        raise ValidationError(f"unknown action {proposal.action!r}")

    # (2) role permission (registry currently role-agnostic; roles.yaml narrows)
    # (3) args schema
    try:
        args = spec.arg_schema.model_validate(proposal.args)
    except PydValidationError as e:
        raise ValidationError(f"invalid args for {proposal.action}: {e.errors()[0].get('msg', 'invalid')}") from e

    # (4) preconditions: energy, funds, job state
    cost = spec.energy_cost
    if cost > 0 and agent.vitals.energy < cost:
        raise PreconditionFailed(f"needs {cost} energy, has {agent.vitals.energy}")
    if spec.coin_cost > 0 and agent.vitals.funds < spec.coin_cost:
        raise PreconditionFailed(f"needs {spec.coin_cost} coins, has {agent.vitals.funds}")

    # (5) rate limits: 1 action per agent per tick enforced by scheduler; budgets here
    # (6) idempotency
    key = idempotency_key(agent.id, world.tick, proposal.action, proposal.args)
    if key in seen_keys:
        raise IdempotencyError("duplicate proposal this tick")
    seen_keys.add(key)

    return spec, args


def compute_energy_cost(spec: Any, args: Any) -> int:
    """Energy for this action (effort multipliers)."""
    if getattr(spec, "energy_per_effort", 0):
        return int(spec.energy_per_effort) * int(getattr(args, "effort", 1))
    return max(int(spec.energy_cost), 0)


def apply_energy(world: World, agent: AgentState, delta: int) -> None:
    """Clamp energy to [0, 100]."""
    agent.vitals.energy = max(0, min(100, agent.vitals.energy + delta))


def execute(
    world: World,
    agent: AgentState,
    proposal: Proposal,
    ledger: LedgerWriter,
    events: EventLog,
    seen_keys: set[str],
    handlers: dict[str, Any],
) -> ActionResult:
    """Full gateway path: validate -> handler -> energy/events/result. Fail closed on errors."""
    tick = world.tick
    try:
        spec, args = validate_and_build(world, agent, proposal, seen_keys)
        ctx = ActionContext(world=world, agent=agent, ledger=ledger, events=events, tick=tick)
        handler = handlers.get(proposal.action)
        if handler is None:
            raise ValidationError(f"no handler for {proposal.action}")
        handler.validate(ctx, args)
        energy_cost = compute_energy_cost(spec, args)
        result: ActionResult = handler.execute(ctx, args)
    except ValidationError as e:
        agent.vitals.strikes += 1
        _emit_rejected(events, world, agent, proposal, str(e), strike=True)
        return ActionResult(status="rejected", reject_reason=str(e), observation=f"rejected: {e}")
    except PreconditionFailed as e:
        _emit_rejected(events, world, agent, proposal, str(e), strike=False)
        return ActionResult(status="rejected", reject_reason=str(e), observation=f"rejected: {e}")
    except IdempotencyError as e:
        _emit_rejected(events, world, agent, proposal, str(e), strike=False)
        return ActionResult(status="rejected", reject_reason=str(e), observation=f"duplicate: {e}")
    except Exception as e:  # fail closed (AGENTS rule 3)
        msg = f"gateway error: {e}"
        events.emit(world.id, tick=tick, type_="action_error", agent_id=agent.id, payload={"error": str(e)})
        return ActionResult(status="error", reject_reason=msg, observation=msg)

    if energy_cost > 0:
        apply_energy(world, agent, -energy_cost)
    if not result.energy_cost:
        result.energy_cost = energy_cost
    events.emit(
        world.id, tick=tick, type_="action_accepted", agent_id=agent.id,
        payload={"action": proposal.action, "args": proposal.args},
    )
    return result


def _emit_rejected(events: EventLog, world: World, agent: AgentState, proposal: Proposal, reason: str, *, strike: bool) -> None:
    events.emit(
        world.id, tick=world.tick, type_="action_rejected", agent_id=agent.id,
        payload={"action": proposal.action, "reason": reason, "strike": strike},
    )


def take_job_guard(world: World, agent: AgentState, board: JobBoard, job_id: str) -> Any:
    """Shared precondition checks for take_job: OPEN, role match, rep floor, concurrency cap (I7)."""
    job = world.jobs.get(job_id)
    if job is None:
        raise PreconditionFailed(f"job {job_id} not found")
    if job.status != JobStatus.OPEN:
        raise PreconditionFailed(f"job {job_id} not open")
    if job.role != agent.role:
        raise PreconditionFailed(f"job role {job.role} != agent role {agent.role}")
    if agent.vitals.reputation < job.min_reputation:
        raise PreconditionFailed(f"reputation {agent.vitals.reputation} below floor {job.min_reputation}")
    eco = world.economy
    max_conc = eco.max_concurrent_jobs if eco else 1
    held = sum(1 for j in world.jobs.values() if j.assigned_agent == agent.id and j.status == JobStatus.TAKEN)
    if held >= max_conc:
        raise PreconditionFailed(f"already holds {held} jobs (max {max_conc})")
    return job
