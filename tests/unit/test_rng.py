"""T0.3: DeterministicRNG - same inputs give same streams; purposes never collide."""

from __future__ import annotations

import random

from hypothesis import given
from hypothesis import strategies as st

from agentville.rng import derive_rng


def test_same_inputs_same_stream() -> None:
    a = derive_rng(11, 5, "jobs")
    b = derive_rng(11, 5, "jobs")
    assert [a.random() for _ in range(10)] == [b.random() for _ in range(10)]


def test_different_purpose_different_stream() -> None:
    a = derive_rng(11, 5, "jobs")
    b = derive_rng(11, 5, "order")
    assert [a.random() for _ in range(10)] != [b.random() for _ in range(10)]


def test_agent_scoping_changes_stream() -> None:
    a = derive_rng(11, 5, "decide", "agent_0001")
    b = derive_rng(11, 5, "decide", "agent_0002")
    assert [a.random() for _ in range(10)] != [b.random() for _ in range(10)]


def test_returns_random_random() -> None:
    assert isinstance(derive_rng(1, 1, "x"), random.Random)


@given(seed=st.integers(min_value=0, max_value=2**31), tick=st.integers(min_value=0, max_value=10**6))
def test_seed_tick_determinism_property(seed: int, tick: int) -> None:
    r1 = derive_rng(seed, tick, "p")
    r2 = derive_rng(seed, tick, "p")
    assert r1.random() == r2.random()


@given(
    seed=st.integers(min_value=0, max_value=2**31),
    tick=st.integers(min_value=0, max_value=10**6),
)
def test_purpose_independence_property(seed: int, tick: int) -> None:
    draws_p1 = [derive_rng(seed, tick, "alpha").random() for _ in range(1)]
    draws_p2 = [derive_rng(seed, tick, "beta").random() for _ in range(1)]
    assert draws_p1 != draws_p2
