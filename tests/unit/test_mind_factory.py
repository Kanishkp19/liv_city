"""Mind factory: mode selection for mock vs live LLM minds."""

from __future__ import annotations

import pytest

from agentville.engine.mind_factory import build_minds


def _agents() -> dict:
    return {"agent_000001": object(), "agent_000002": object()}


def test_mock_mode_default() -> None:
    minds = build_minds(_agents(), session=None, mode="mock", mock_policy="oracle")
    assert set(minds) == set(_agents())
    assert all(type(m).__name__ == "MockMind" for m in minds.values())


def test_llm_mode_builds_gateway_minds() -> None:
    minds = build_minds(_agents(), session=None, mode="llm")
    assert set(minds) == set(_agents())
    assert all(type(m).__name__ == "LLMMind" for m in minds.values())
    # every agent shares one gateway instance
    gws = {id(m.gw) for m in minds.values()}
    assert len(gws) == 1


def test_unknown_mode_raises() -> None:
    with pytest.raises(ValueError, match="unknown mind mode"):
        build_minds(_agents(), session=None, mode="psychic")
