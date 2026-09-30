"""World <-> DB persistence via snapshots (state) + world row bookkeeping."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from agentville.config import load_economy
from agentville.db.models import Agent as AgentRow
from agentville.db.models import Job as JobRow
from agentville.db.models import Snapshot
from agentville.db.models import World as WorldRow
from agentville.engine.presets import Preset
from agentville.engine.types import AgentState, GroupType, Vitals
from agentville.engine.world import World


def _unique_world_id(seed: int, session: Session) -> str:
    """Collision-free world id: seed + row count (deterministic, no wall time in engine)."""
    from sqlalchemy import func, select

    n = session.scalar(select(func.count()).select_from(WorldRow)) or 0
    wid = f"world_{seed:06d}_{n + 1:03d}"
    while session.get(WorldRow, wid) is not None:
        n += 1
        wid = f"world_{seed:06d}_{n + 1:03d}"
    return wid


def create_world(session: Session, *, name: str, preset_name: str, seed: int, world_id: str | None = None) -> World:
    """Create a world from a preset, persist its row, return the aggregate."""
    preset = Preset.load(preset_name)
    eco = load_economy()
    wid = world_id or _unique_world_id(seed, session)
    world = World(id=wid, name=name, seed=seed, preset=preset_name, economy=eco, config=dict(preset.model_dump()))
    # starting agents
    for spec in preset.agents:
        for _ in range(spec.count):
            aid = world.ids.next("agent")
            world.agents[aid] = AgentState(
                id=aid, world_id=wid, role=spec.role, group_type=GroupType(spec.group),
                vitals=Vitals(energy=100, funds=eco.starting_funds, reputation=50.0),
                born_tick=0,
            )
            world.accounts[f"agent:{aid}"] = eco.starting_funds
    row = WorldRow(
        id=wid, name=name, seed=seed, preset=preset_name, tick=0, status="created", mode="live",
        config_json=json.dumps(world.config), event_hash="", created_at=world.clock.now_iso(),
    )
    session.add(row)
    session.flush()
    sync_agents(session, world)
    return world


def sync_agents(session: Session, world: World) -> None:
    """Upsert one agents row per in-memory agent (FK target for artifacts/actions)."""
    for aid, a in world.agents.items():
        row = session.get(AgentRow, aid)
        if row is None:
            session.add(AgentRow(
                id=aid, world_id=world.id, role=a.role, generation=a.generation,
                parent_id=a.parent_id, group_type=a.group_type.value, status=a.status.value,
                born_tick=a.born_tick, name=aid, location=a.location,
                current_job_id=a.current_job_id, inventory_json=json.dumps(a.inventory),
                idle_ticks=a.idle_ticks, low_energy_ticks=a.low_energy_ticks,
                negative_funds_ticks=a.negative_funds_ticks,
            ))
        else:
            row.status = a.status.value
            row.current_job_id = a.current_job_id
            row.location = a.location
            row.idle_ticks = a.idle_ticks
            row.low_energy_ticks = a.low_energy_ticks
            row.negative_funds_ticks = a.negative_funds_ticks
            row.inventory_json = json.dumps(a.inventory)
    session.flush()


def sync_jobs(session: Session, world: World) -> None:
    """Upsert jobs rows for all known jobs (FK target for artifacts/verifications)."""
    for jid, j in world.jobs.items():
        row = session.get(JobRow, jid)
        if row is None:
            session.add(JobRow(
                id=jid, world_id=world.id, buyer_id=j.buyer_id, role=j.role, title=j.title,
                brief=j.brief, params_json=json.dumps(j.params),
                visible_params_json=json.dumps(j.visible_params),
                verifier_recipe_json=j.verifier_recipe.model_dump_json(),
                reward=j.reward, penalty=j.penalty, difficulty=j.difficulty,
                min_reputation=j.min_reputation, posted_tick=j.posted_tick,
                deadline_tick=j.deadline_tick, status=j.status.value,
                assigned_agent=j.assigned_agent, is_audit_plant=j.is_audit_plant,
            ))
        else:
            row.status = j.status.value
            row.assigned_agent = j.assigned_agent
    session.flush()


def save_snapshot(session: Session, world: World) -> None:
    """Upsert the snapshot row for the current tick."""
    existing = session.scalar(
        select(Snapshot).where(Snapshot.world_id == world.id, Snapshot.tick == world.tick)
    )
    state_json = world.snapshot_json()
    if existing:
        existing.state_json = state_json
        existing.event_hash = world.event_hash
    else:
        session.add(Snapshot(world_id=world.id, tick=world.tick, state_json=state_json, event_hash=world.event_hash))
    session.flush()


def load_world(session: Session, world_id: str) -> World:
    """Rebuild the World aggregate from its latest snapshot."""
    snap = session.execute(
        select(Snapshot).where(Snapshot.world_id == world_id).order_by(Snapshot.tick.desc()).limit(1)
    ).scalar_one_or_none()
    if snap is None:
        msg = f"no snapshot for world {world_id}"
        raise ValueError(msg)
    world = World(id=world_id, name="", seed=0, preset="")
    world.restore(json.loads(snap.state_json))
    world.economy = load_economy()
    return world


def set_world_status(session: Session, world_id: str, status: str) -> None:
    """Update the world row status (created/running/paused/halted/done)."""
    row = session.get(WorldRow, world_id)
    if row is not None:
        row.status = status
        session.flush()
