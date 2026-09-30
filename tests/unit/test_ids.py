"""T0.3: IdGen - counter-based deterministic ids like agent_0007."""

from __future__ import annotations

from agentville.ids import IdGen


def test_format_matches_docs() -> None:
    """Docs show agent_0007 and job_000123; standardized to 6-digit (DECISIONS D8)."""
    gen = IdGen()
    gen.next("agent")
    gen.next("agent")
    assert gen.next("agent") == "agent_000003"


def test_zero_padded_to_six() -> None:
    gen = IdGen()
    assert gen.next("job") == "job_000001"


def test_kinds_count_independently() -> None:
    gen = IdGen()
    assert gen.next("agent") == "agent_000001"
    assert gen.next("job") == "job_000001"
    assert gen.next("agent") == "agent_000002"


def test_monotonic_within_kind() -> None:
    gen = IdGen()
    seen = [int(gen.next("agent").split("_")[1]) for _ in range(50)]
    assert seen == sorted(seen)
