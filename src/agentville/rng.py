"""Deterministic randomness: all engine entropy derives from (seed, tick, purpose, agent_id)."""

from __future__ import annotations

import hashlib
import random


def derive_rng(
    seed: int,
    tick: int,
    purpose: str,
    agent_id: str | None = None,
) -> random.Random:
    """Return a Random seeded by sha256("seed:tick:purpose[:agent_id]") per TRD S5."""
    key = f"{seed}:{tick}:{purpose}"
    if agent_id is not None:
        key = f"{key}:{agent_id}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return random.Random(int(digest, 16))
