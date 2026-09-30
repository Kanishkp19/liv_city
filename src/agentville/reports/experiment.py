"""Experiment 01: multi-seed runner + deterministic report (AGENT_ROLES S8, T5.x)."""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any

from agentville.engine.mocks import MockMind
from agentville.engine.persistence import create_world, set_world_status
from agentville.engine.scheduler import Scheduler


def run_seed(session: Any, seed: int, ticks: int, groups: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run one world; returns per-group metrics (deterministic per seed)."""
    w = create_world(session, name=f"exp01_s{seed}", preset_name="experiment01", seed=seed)
    set_world_status(session, w.id, "running")
    minds: dict[str, MockMind] = {}
    for aid, agent in w.agents.items():
        minds[aid] = MockMind("oracle" if agent.group_type.value == "learner" else "random_valid")
    sched = Scheduler(w, session, minds)
    for _ in range(ticks):
        sched.run_tick()
        session.commit()
    set_world_status(session, w.id, "done")
    return _metrics(w)


def _metrics(w: Any) -> dict[str, Any]:
    """Per-group aggregates from a finished world."""
    out: dict[str, Any] = {}
    for agent in w.agents.values():
        g = agent.group_type.value
        d = out.setdefault(g, {"survivors": 0, "total": 0, "funds": [], "alive_ticks": []})
        d["total"] += 1
        d["funds"].append(agent.vitals.funds)
        d["alive_ticks"].append(w.tick - agent.born_tick if agent.status != "dead" else agent.born_tick)
        if agent.status != "dead":
            d["survivors"] += 1
    for d in out.values():
        d["survival_rate"] = d["survivors"] / d["total"] if d["total"] else 0
        d["median_funds"] = statistics.median(d["funds"]) if d["funds"] else 0
        del d["funds"]
    return out


def run_experiment(session: Any, seeds: list[int], ticks: int = 150) -> dict[str, Any]:
    """All seeds; aggregate per-group across seeds with paired stats."""
    per_seed: dict[int, dict[str, Any]] = {}
    for seed in seeds:
        per_seed[seed] = run_seed(session, seed, ticks)
    groups: dict[str, dict[str, list[float]]] = {}
    for seed_m in per_seed.values():
        for g, d in seed_m.items():
            groups.setdefault(g, {"survival": [], "funds": []})
            groups[g]["survival"].append(d["survival_rate"])
            groups[g]["funds"].append(d["median_funds"])
    return {
        "seeds": seeds, "ticks": ticks, "per_seed": {str(s): m for s, m in per_seed.items()},
        "groups": {g: {"survival_mean": statistics.mean(v["survival"]),
                       "funds_mean": statistics.mean(v["funds"])} for g, v in groups.items()},
    }


def wilcoxon_signed_rank(x: list[float], y: list[float]) -> tuple[float, float]:
    """Plain Wilcoxon signed-rank (no scipy); returns (W, two-sided p normal approx)."""
    import math

    diffs = [a - b for a, b in zip(x, y, strict=False) if a != b]
    if not diffs:
        return 0.0, 1.0
    ranked = sorted((abs(d), i) for i, d in enumerate(diffs))
    ranks = [0.0] * len(diffs)
    i = 0
    while i < len(ranked):
        j = i
        while j < len(ranked) and ranked[j][0] == ranked[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2
        for k in range(i, j):
            ranks[ranked[k][1]] = avg_rank
        i = j
    w_plus = sum(r for r, d in zip(ranks, diffs, strict=True) if d > 0)
    n = len(diffs)
    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (w_plus - mu) / sigma if sigma else 0.0
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return w_plus, min(p, 1.0)


def render_report(result: dict[str, Any], out_path: Path) -> Path:
    """Deterministic markdown report (same DB -> same bytes)."""
    lines = [
        "# Experiment 01 report",
        "",
        f"Seeds: {result['seeds']} | Ticks: {result['ticks']}",
        "",
        "| group | survival mean | funds mean |",
        "|---|---|---|",
    ]
    for g in sorted(result["groups"]):
        d = result["groups"][g]
        lines.append(f"| {g} | {d['survival_mean']:.3f} | {d['funds_mean']:.1f} |")
    if {"control_a", "learner"} <= set(result["groups"]):
        a = [result["per_seed"].get(s, {}).get("control_a", {}).get("survival_rate", 0) for s in map(str, result["seeds"])]
        ln = [result["per_seed"].get(s, {}).get("learner", {}).get("survival_rate", 0) for s in map(str, result["seeds"])]
        w_stat, p = wilcoxon_signed_rank(ln, a)
        lines += ["", f"Wilcoxon learner vs control_a: W={w_stat:.1f}, p={p:.4f}"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
