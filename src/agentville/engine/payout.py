"""Payout computation (TRD S7): tier math, late multiplier, reputation deltas."""

from __future__ import annotations

from agentville.engine.types import Coins


def tier_multiplier(quality: float, tiers: list[list[float]]) -> float:
    """Multiplier of the HIGHEST threshold <= quality (e.g. q=0.8 -> the 0.75 tier)."""
    for threshold, mult in sorted(tiers, key=lambda t: t[0], reverse=True):
        if quality >= threshold:
            return float(mult)
    return 0.0


def compute_payout(
    *,
    base_reward: Coins,
    quality: float,
    quality_tiers: list[list[float]],
    late: bool,
    late_multiplier: float,
) -> Coins:
    """payout = floor(base * tier_mult * late_mult); 0 when quality below lowest positive tier."""
    if quality < quality_tiers[-1][0] if quality_tiers else False:
        pass
    mult = tier_multiplier(quality, quality_tiers)
    if mult <= 0:
        return 0
    lm = late_multiplier if late else 1.0
    return int(base_reward * mult * lm)


def reputation_delta(quality: float, deltas: dict[str, float]) -> float:
    """Reputation change by quality band (excellent/good/ok/fail)."""
    if quality >= 0.9:
        return float(deltas.get("excellent", 3))
    if quality >= 0.75:
        return float(deltas.get("good", 1))
    if quality >= 0.6:
        return float(deltas.get("ok", 0))
    return float(deltas.get("fail", -5))
