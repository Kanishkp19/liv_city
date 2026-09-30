"""T1.1/T1.2: World snapshot/restore determinism + preset loading."""

from __future__ import annotations

import pytest

from agentville.config import load_economy
from agentville.engine.presets import Preset
from agentville.engine.types import AgentState, GroupType, Vitals
from agentville.engine.world import World


def _mk_world(seed: int = 11) -> World:
    w = World(id="w1", name="t", seed=seed, preset="small_city", economy=load_economy())
    for i in range(3):
        aid = f"agent_{i:06d}"
        w.agents[aid] = AgentState(
            id=aid, world_id="w1", role="content_creator", group_type=GroupType.LEARNER,
            vitals=Vitals(energy=100, funds=500, reputation=50.0),
        )
    w.accounts = {"treasury": 10_000, "agent:agent_000000": 500}
    return w


def test_snapshot_restore_identical_hash() -> None:
    w = _mk_world()
    snap = w.snapshot()
    w2 = World(id="x", name="x", seed=0, preset="x")
    w2.restore(snap)
    assert w2.state_hash() == w.state_hash()


def test_mutations_change_hash() -> None:
    w = _mk_world()
    h1 = w.state_hash()
    w.tick = 5
    assert w.state_hash() != h1


def test_rng_deterministic_per_tick_purpose() -> None:
    w = _mk_world()
    a = [w.rng("jobs").random() for _ in range(5)]
    w.tick += 1
    b = [w.rng("jobs").random() for _ in range(5)]
    w.tick -= 1
    c = [w.rng("jobs").random() for _ in range(5)]
    assert a == c and a != b


def test_alive_and_role_filters() -> None:
    w = _mk_world()
    w.agents["agent_000000"].status = "dead"
    assert len(w.alive_agents()) == 2
    assert len(w.agents_by_role("content_creator")) == 2


def test_preset_loads_small_city() -> None:
    p = Preset.load("small_city")
    assert p.districts[0] == "housing"
    assert p.agents[0].role == "content_creator"
    assert p.buyers["companies"] == 4


def test_preset_missing_raises(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(FileNotFoundError):
        Preset.load("nope", base_dir=tmp_path)
