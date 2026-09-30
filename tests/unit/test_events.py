"""T0.6: EventLog hash chain (invariant I8)."""

from __future__ import annotations

import pytest

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from agentville.db.models import World
from agentville.engine.events import EventLog

pytestmark = pytest.mark.phase0


@pytest.fixture()
def world(session: Session) -> str:
    session.add(World(id="w1", name="t", seed=11, preset="p", config_json="{}", created_at="2026"))
    session.flush()
    return "w1"


def test_emit_assigns_seq_and_chain(session: Session, world: str) -> None:
    log = EventLog(session)
    e1 = log.emit(world, tick=1, type_="tick_started", agent_id=None, payload={"tick": 1})
    e2 = log.emit(world, tick=1, type_="job_posted", agent_id=None, payload={"job": "j1"})
    e3 = log.emit(world, tick=2, type_="tick_started", agent_id=None, payload={"tick": 2})
    assert (e1, e2, e3) == (1, 2, 3)
    rows = log.rows(world)
    assert [r.seq for r in rows] == [0, 1, 0]  # per-tick seq restarts
    assert rows[1].prev_hash == rows[0].hash  # chain links
    assert rows[2].prev_hash == rows[1].hash


def test_verify_chain_ok(session: Session, world: str) -> None:
    log = EventLog(session)
    for t in range(1, 4):
        log.emit(world, tick=t, type_="tick_started", agent_id=None, payload={"tick": t})
    assert log.verify_chain(world) is True


def test_verify_chain_detects_tampering(session: Session, world: str, engine: Engine) -> None:
    log = EventLog(session)
    for t in range(1, 4):
        log.emit(world, tick=t, type_="tick_started", agent_id=None, payload={"tick": t})
    session.commit()
    # simulate tamper: bypass append-only trigger (defensive layer tested separately)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TRIGGER events_no_update")
        conn.exec_driver_sql("UPDATE events SET payload_json = '{\"tick\": 999}' WHERE id = 2")
        conn.exec_driver_sql("CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END")
    assert log.verify_chain(world) is False


def test_head_hash_advances(session: Session, world: str) -> None:
    log = EventLog(session)
    assert log.head(world) == ""
    log.emit(world, tick=1, type_="t", agent_id=None, payload={})
    assert log.head(world) != ""
