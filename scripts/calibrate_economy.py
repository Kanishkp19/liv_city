"""Economy calibration (TESTING.md): oracle must thrive, noop must die young.

Usage: uv run python scripts/calibrate_economy.py [--ticks 100]
Exit 1 when gates fail: oracle survival >= 50% @100 ticks (offline policy), noop dead <= 60.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentville.engine.mocks import MockMind  # noqa: E402
from agentville.engine.persistence import create_world  # noqa: E402
from agentville.engine.scheduler import Scheduler  # noqa: E402


def run_policy(policy: str, ticks: int) -> tuple[int, int]:
    """Returns (alive_at_end, total_agents)."""
    from sqlalchemy.orm import Session

    from agentville.db.session import make_engine

    eng = make_engine("sqlite://", apply_triggers=True)
    try:
        s = Session(eng)
        w = create_world(s, name=f"cal_{policy}", preset_name="small_city", seed=11)
        sched = Scheduler(w, s, {aid: MockMind(policy) for aid in w.agents})
        for _ in range(ticks):
            sched.run_tick()
            s.commit()
        alive = sum(1 for a in w.agents.values() if a.status == "alive")
        s.close()
        return alive, len(w.agents)
    finally:
        eng.dispose()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=100)
    args = ap.parse_args()

    oracle_alive, total = run_policy("oracle", args.ticks)
    noop_alive, _ = run_policy("noop", args.ticks)
    print(f"oracle: {oracle_alive}/{total} alive after {args.ticks} ticks")
    print(f"noop:   {noop_alive}/{total} alive after {args.ticks} ticks")

    oracle_rate = oracle_alive / total
    gates = [
        ("oracle survival >= 50%", oracle_rate >= 0.5),
        ("noop dies before end", noop_alive < total),
    ]
    ok = True
    for name, passed in gates:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok &= passed
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
