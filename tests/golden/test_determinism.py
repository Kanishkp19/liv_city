"""T1.9 golden determinism: same seed -> identical event hash chains."""

from __future__ import annotations

import pytest

from agentville.engine.mocks import MockMind
from agentville.engine.persistence import create_world
from agentville.engine.scheduler import Scheduler


def _run(seed: int, ticks: int) -> tuple[str, int]:
    from agentville.db.session import make_engine
    from sqlalchemy.orm import Session

    eng = make_engine("sqlite://", apply_triggers=True)
    try:
        s = Session(eng)
        w = create_world(s, name="g", preset_name="small_city", seed=seed)
        sched = Scheduler(w, s, {aid: MockMind("oracle") for aid in w.agents})
        for _ in range(ticks):
            sched.run_tick()
            s.commit()
        from agentville.engine.events import EventLog

        head = EventLog(s).head(w.id)
        payout = sum(r.payout_total for r in sched.reports)
        s.close()
        return head, payout
    finally:
        eng.dispose()


@pytest.mark.phase1
def test_same_seed_identical_event_chain() -> None:
    h1, p1 = _run(11, 15)
    h2, p2 = _run(11, 15)
    assert h1 == h2 and h1
    assert p1 == p2


@pytest.mark.phase1
def test_different_seed_different_chain() -> None:
    h1, _ = _run(11, 15)
    h2, _ = _run(22, 15)
    assert h1 != h2
