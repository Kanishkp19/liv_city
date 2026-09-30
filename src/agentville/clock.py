"""Simulation clock. Wall-clock time is quarantined here (AGENTS.md rule 4)."""

from __future__ import annotations

from datetime import UTC, datetime


class Clock:
    """Tick counter with an isolated wall-clock accessor for created_at fields."""

    def __init__(self, tick: int = 0) -> None:
        self.tick = tick

    def advance(self) -> int:
        """Move to the next tick and return it."""
        self.tick += 1
        return self.tick

    def now_iso(self) -> str:
        """UTC ISO-8601 timestamp for audit columns only (never engine logic)."""
        return datetime.now(UTC).isoformat()
