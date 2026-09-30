"""Succession: successor spawn, group-specific lessons, pivot rule (TRD S3.5)."""

from __future__ import annotations

from typing import Any

from agentville.engine.types import AgentState, AgentStatus, GroupType, Vitals
from agentville.engine.world import World


def spawn_successor(
    world: World,
    dead: AgentState,
    autopsy: dict[str, Any],
    *,
    successor_funds: int,
    role_earnings_stats: dict[str, float] | None = None,
    open_per_role: dict[str, int] | None = None,
    agents_per_role: dict[str, int] | None = None,
) -> AgentState:
    """Same role by default; pivot when dead role under-earns and another role has surplus.

    Controls A/B/C inherit no lessons; learners inherit top-3 lessons (docs S6).
    """
    role = dead.role
    pivot_to = _maybe_pivot(role, role_earnings_stats or {}, open_per_role or {}, agents_per_role or {})
    if pivot_to:
        role = pivot_to
    new_id = world.ids.next("agent")
    inherits_lessons = dead.group_type == GroupType.LEARNER
    lessons = autopsy.get("lessons", [])[:3] if inherits_lessons else []
    starter = autopsy.get("starter_playbook_md") if inherits_lessons else ""
    successor = AgentState(
        id=new_id, world_id=world.id, role=role, generation=dead.generation + 1,
        parent_id=dead.id, group_type=dead.group_type,
        vitals=Vitals(energy=100, funds=successor_funds, reputation=50.0),
        born_tick=world.tick,
        inventory={k: v for k, v in dead.inventory.items() if k != "better_mic"},  # tools non-transferable per docs silence; keep conservative
    )
    world.agents[new_id] = successor
    world.accounts[f"agent:{new_id}"] = successor_funds
    if lessons:
        successor_notes = world.config.setdefault("_successor_notes", {})
        successor_notes[new_id] = lessons
    if starter:
        successor_notes = world.config.setdefault("_successor_playbooks", {})
        successor_notes[new_id] = starter
    return successor


def _maybe_pivot(
    dead_role: str,
    role_earnings: dict[str, float],
    open_per_role: dict[str, int],
    agents_per_role: dict[str, int],
) -> str | None:
    """Pivot if dead role's mean earnings/tick is below the 25th pct of OTHER roles
    and some role has job surplus (open/agents > 2) - docs AGENT_ROLES S6."""
    others = sorted(v for r, v in role_earnings.items() if r != dead_role)
    if not others:
        return None
    idx = max(0, int(0.25 * (len(others) - 1)))
    p25 = others[idx]
    if role_earnings.get(dead_role, 0) >= p25:
        return None
    best: tuple[str, float] | None = None
    for role, open_n in open_per_role.items():
        agents_n = agents_per_role.get(role, 0)
        surplus = open_n / agents_n if agents_n else float("inf")
        if agents_n > 0 and surplus > 2 and (best is None or surplus > best[1]):
            best = (role, surplus)
    return best[0] if best else None


def mark_dead(world: World, agent_id: str) -> None:
    """Set DEAD status (jobs released by lifecycle.kill)."""
    agent = world.agents.get(agent_id)
    if agent is not None:
        agent.status = AgentStatus.DEAD
