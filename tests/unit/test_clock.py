"""T0.3: Clock - tick counter advances deterministically; wall time only via now_iso."""

from __future__ import annotations

import re
from pathlib import Path

from agentville.clock import Clock


def test_tick_starts_at_zero_and_advances() -> None:
    c = Clock()
    assert c.tick == 0
    assert c.advance() == 1
    assert c.advance() == 2
    assert c.tick == 2


def test_now_iso_is_iso8601_utc() -> None:
    iso = Clock().now_iso()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", iso)
    assert iso.endswith("+00:00")


def test_engine_has_no_banned_nondeterminism() -> None:
    """AGENTS.md rule 4: no random/time.time/uuid4 in engine logic (Clock is the sanctioned exception)."""
    engine_dir = Path("src/agentville/engine")
    banned = ["import random", "from random", "time.time(", "uuid4(", "datetime.now("]
    violations: list[str] = []
    for py in engine_dir.rglob("*.py"):
        if py.name == "clock.py":
            continue  # wall time is quarantined there by design
        text = py.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                violations.append(f"{py}:{token}")
    assert violations == []
