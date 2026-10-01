"""AgentVille CLI (typer): new-world, run, inspect, replay, report, demo."""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer

app = typer.Typer(help="AgentVille command line", no_args_is_help=True)

POLICIES = ["oracle", "noop", "random_valid", "adversarial"]


def _open_session(db_url: str | None) -> tuple[Any, Any]:
    from agentville.config import load_settings
    from agentville.db.session import make_engine, make_session_factory

    url = db_url or load_settings().db_url
    engine = make_engine(url, apply_triggers=True)
    return engine, make_session_factory(engine)()


@app.command()
def new_world(
    name: str = typer.Option("demo", help="World name"),
    preset: str = typer.Option("small_city", help="Preset name"),
    seed: int = typer.Option(11, help="World seed"),
) -> None:
    """Create a world row + initial snapshot."""
    from agentville.engine.persistence import create_world, save_snapshot

    engine, session = _open_session(None)
    try:
        world = create_world(session, name=name, preset_name=preset, seed=seed)
        save_snapshot(session, world)
        session.commit()
        typer.echo(f"created {world.id} (seed={seed}, preset={preset}, agents={len(world.agents)})")
    finally:
        engine.dispose()


@app.command()
def run(
    world_id: Annotated[str | None, typer.Option()] = None,
    ticks: int = typer.Option(20, help="Number of ticks"),
    mock: str = typer.Option("oracle", help="Mock policy for all agents"),
    mode: str = typer.Option("mock", help="mind mode: mock | llm (live gateway)"),
    db_url: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Run ticks headless (mock or live LLM minds via --mode llm)."""
    from agentville.engine.mind_factory import build_minds
    from agentville.engine.persistence import load_world, save_snapshot, set_world_status
    from agentville.engine.scheduler import Scheduler

    engine, session = _open_session(db_url)
    try:
        world = load_world(session, world_id) if world_id else _fresh_world(session)
        set_world_status(session, world.id, "running")
        minds = build_minds(world.agents, session, mode=mode, mock_policy=mock)
        sched = Scheduler(world, session, minds)
        totals = {"payout": 0, "deaths": 0, "passes": 0}
        for _ in range(ticks):
            r = sched.run_tick()
            session.commit()
            totals["payout"] += r.payout_total
            totals["deaths"] += len(r.deaths)
            totals["passes"] += r.passes
        save_snapshot(session, world)
        set_world_status(session, world.id, "paused")
        session.commit()
        typer.echo(
            f"{world.id}: ran {ticks} ticks -> passes={totals['passes']} "
            f"payout={totals['payout']} deaths={totals['deaths']} hash={world.event_hash[:12]}"
        )
    finally:
        engine.dispose()


def _fresh_world(session: Any) -> Any:
    from agentville.engine.persistence import create_world, save_snapshot

    w = create_world(session, name="cli", preset_name="small_city", seed=11)
    save_snapshot(session, w)
    session.commit()
    return w


@app.command()
def inspect(
    world_id: str = typer.Argument(...),
    db_url: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Print world summary: tick, agents, funds, jobs."""
    from agentville.engine.persistence import load_world

    engine, session = _open_session(db_url)
    try:
        w = load_world(session, world_id)
        alive = [a for a in w.agents.values() if a.status == "alive"]
        typer.echo(json.dumps({
            "world": w.id, "tick": w.tick, "hash": w.event_hash[:12],
            "agents": len(w.agents), "alive": len(alive),
            "jobs": len(w.jobs), "money_supply": sum(w.accounts.values()),
        }, indent=2))
    finally:
        engine.dispose()


@app.command()
def replay(
    world_id: str = typer.Argument(...),
    until_tick: int = typer.Option(0, help="0 = full"),
    db_url: Annotated[str | None, typer.Option()] = None,
) -> None:
    """Verify the event hash chain of a stored world (full replay lands in P2)."""
    from agentville.engine.events import EventLog

    engine, session = _open_session(db_url)
    try:
        ok = EventLog(session).verify_chain(world_id)
        typer.echo(f"chain {'OK' if ok else 'BROKEN'} for {world_id}")
        raise typer.Exit(0 if ok else 1)
    finally:
        engine.dispose()


@app.command()
def experiment(
    seeds: str = typer.Option("11,22,33,44,55", help="Comma-separated seeds"),
    ticks: int = typer.Option(150),
    mock: str = typer.Option("oracle"),
    out: str = typer.Option("reports/exp01.md"),
) -> None:
    """Run Experiment 01 across seeds and render the report."""
    from pathlib import Path

    from agentville.reports.experiment import render_report, run_experiment

    seed_list = [int(x) for x in seeds.split(",") if x.strip()]
    engine, session = _open_session(None)
    try:
        result = run_experiment(session, seed_list, ticks)
        path = render_report(result, Path(out))
        typer.echo(f"experiment done: {len(seed_list)} seeds x {ticks} ticks -> {path}")
    finally:
        engine.dispose()


@app.command()
def demo(ticks: int = typer.Option(20)) -> None:
    """make demo: fresh world + oracle agents + report."""
    from agentville.engine.mocks import MockMind
    from agentville.engine.persistence import create_world, save_snapshot, set_world_status
    from agentville.engine.scheduler import Scheduler

    engine, session = _open_session(None)
    try:
        w = create_world(session, name="demo", preset_name="small_city", seed=11)
        set_world_status(session, w.id, "running")
        minds = {aid: MockMind("oracle") for aid in w.agents}
        sched = Scheduler(w, session, minds)
        for _ in range(ticks):
            sched.run_tick()
            session.commit()
        save_snapshot(session, w)
        set_world_status(session, w.id, "done")
        session.commit()
        passes = sum(r.passes for r in sched.reports)
        payout = sum(r.payout_total for r in sched.reports)
        alive = len([a for a in w.agents.values() if a.status == "alive"])
        typer.echo(f"demo: {ticks} ticks, alive={alive}/{len(w.agents)}, passes={passes}, payout={payout}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    app()
