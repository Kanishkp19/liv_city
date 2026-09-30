"""T0.4: models mirror BACKEND_SCHEMA; round-trip insert/select each table."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from agentville.db.models import (
    Action,
    Agent,
    AgentVital,
    Buyer,
    Company,
    Event,
    Job,
    LedgerEntry,
    World,
)


def _world(s: Session) -> World:
    w = World(id="w1", name="t", seed=11, preset="small_city", config_json="{}", created_at="2026-01-01T00:00:00+00:00")
    s.add(w)
    s.flush()
    return w


def test_world_roundtrip(session: Session) -> None:
    w = _world(session)
    got = session.scalar(select(World).where(World.id == "w1"))
    assert got is not None and got.seed == 11 and w.status == "created"


def _agent(s: Session, id_: str = "agent_000001") -> Agent:
    _world(s)
    a = Agent(id=id_, world_id="w1", role="content_creator", group_type="learner", born_tick=0, name="A")
    s.add(a)
    s.flush()
    return a


def test_agent_roundtrip_and_fk(session: Session) -> None:
    a = _agent(session)
    assert a.idle_ticks == 0 and a.status == "alive"
    orphan = Agent(id="agent_x", world_id="missing", role="r", group_type="learner", born_tick=0, name="B")
    session.add(orphan)
    with pytest.raises(Exception, match="FOREIGN KEY"):
        session.flush()


def test_vitals_roundtrip(session: Session) -> None:
    a = _agent(session)
    session.add(AgentVital(agent_id=a.id, tick=1, energy=90, funds=500, reputation=50.0, strikes=0))
    v = session.scalar(select(AgentVital).where(AgentVital.agent_id == "agent_000001"))
    assert v is not None and v.energy == 90


def test_ledger_roundtrip(session: Session) -> None:
    _world(session)
    session.add(
        LedgerEntry(
            world_id="w1", tick=1, debit_account="treasury", credit_account="buyer:b1",
            amount=500, reason="buyer_fund",
        )
    )
    row = session.scalar(select(LedgerEntry))
    assert row is not None and row.amount == 500


def test_job_roundtrip_with_hidden_params(session: Session) -> None:
    _world(session)
    c = Company(id="c1", world_id="w1", name="C", sector="media", budget=10_000)
    session.add(c)
    session.flush()
    b = Buyer(
        id="b1", world_id="w1", company_id="c1", name="B",
        persona_json="{}", quality_bar=0.7, roles_json=json.dumps(["content_creator"]),
    )
    session.add(b)
    session.flush()
    j = Job(
        id="job_000001", world_id="w1", buyer_id="b1", role="content_creator", title="t",
        brief="b", params_json='{"hidden":1}', visible_params_json="{}", verifier_recipe_json="{}",
        reward=90, difficulty=2, posted_tick=1, deadline_tick=7,
    )
    session.add(j)
    got = session.scalar(select(Job).where(Job.id == "job_000001"))
    assert got is not None and json.loads(got.params_json)["hidden"] == 1
    assert got.status == "open" and got.is_audit_plant is False


def test_event_roundtrip_chain_fields(session: Session) -> None:
    _world(session)
    session.add(Event(world_id="w1", tick=1, seq=0, type="tick_started", payload_json="{}", prev_hash="", hash="h1"))
    e = session.scalar(select(Event))
    assert e is not None and e.prev_hash == "" and e.hash == "h1"


def test_action_idempotency_unique(session: Session) -> None:
    a = _agent(session)
    from sqlalchemy.exc import IntegrityError

    session.add(
        Action(id="a1", world_id="w1", agent_id=a.id, tick=1, action="noop", args_json="{}",
               status="accepted", idempotency_key="k1")
    )
    session.add(
        Action(id="a2", world_id="w1", agent_id=a.id, tick=1, action="noop", args_json="{}",
               status="accepted", idempotency_key="k1")
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_all_24_tables_exist(session: Session) -> None:
    from agentville.db.base import Base

    expected = {
        "worlds", "agents", "agent_vitals", "ledger_entries", "companies", "buyers", "jobs",
        "artifacts", "verifications", "judge_votes", "events", "system_events", "actions",
        "llm_calls", "memory_notes", "playbooks", "skills", "sandbox_runs", "web_fetches",
        "autopsies", "exams", "exam_attempts", "graduates", "market_items", "provider_health",
        "snapshots", "experiments",
    }
    assert set(Base.metadata.tables) == expected
