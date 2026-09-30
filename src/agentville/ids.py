"""Deterministic id generation: per-kind counters (agent_000007 style)."""

from __future__ import annotations


class IdGen:
    """Zero-padded, per-kind monotonic ids, fully deterministic per world."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}

    def next(self, kind: str) -> str:
        """Return the next id for kind, e.g. next("agent") -> agent_000001."""
        n = self._counters.get(kind, 0) + 1
        self._counters[kind] = n
        return f"{kind}_{n:06d}"
