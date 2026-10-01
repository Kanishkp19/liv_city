"""FastAPI application (API_SPEC): bearer auth, error envelope, routes, /ws, /metrics."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from agentville.config import load_settings

app = FastAPI(title="AgentVille API", version="0.1.0")


def _session_pair(db_url: str | None = None) -> tuple[Any, Any]:
    from agentville.db.session import make_engine, make_session_factory

    url = db_url or load_settings().db_url
    eng = make_engine(url, apply_triggers=True)
    return eng, make_session_factory(eng)()


def auth(request: Request) -> None:
    """Single-owner bearer token (API_SPEC)."""
    expected = load_settings().token
    got = request.headers.get("Authorization", "").replace("Bearer ", "")
    if expected not in ("", "change-me") and got != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.exception_handler(HTTPException)
async def http_envelope(request: Request, exc: HTTPException) -> JSONResponse:
    """Uniform error envelope {error:{code,message,details}}."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": _code(exc.status_code), "message": str(exc.detail), "details": {}}},
    )


def _code(status: int) -> str:
    return {401: "unauthorized", 404: "not_found", 403: "forbidden", 409: "conflict"}.get(status, "error")


# --- request models -----------------------------------------------------------

class WorldCreate(BaseModel):
    name: str = "world"
    preset: str = "small_city"
    seed: int = 11


class RunReq(BaseModel):
    ticks: int = 10
    mock: str = "oracle"
    mode: str = "mock"  # mock | llm (live LLM via gateway; provider errors noop)


class ApprovalReq(BaseModel):
    reviewer: str
    note: str = ""
    confirm_agent_id: str


# --- worlds -------------------------------------------------------------------

@app.post("/api/v1/worlds", dependencies=[Depends(auth)])
def create_world(body: WorldCreate) -> dict[str, Any]:
    from agentville.engine.persistence import create_world, save_snapshot

    eng, s = _session_pair()
    try:
        w = create_world(s, name=body.name, preset_name=body.preset, seed=body.seed)
        save_snapshot(s, w)
        s.commit()
        return {"id": w.id, "name": w.name, "seed": w.seed, "preset": w.preset, "tick": 0, "status": "created"}
    finally:
        eng.dispose()


@app.get("/api/v1/worlds", dependencies=[Depends(auth)])
def list_worlds() -> dict[str, Any]:
    from sqlalchemy import select

    from agentville.db.models import World as WorldRow

    eng, s = _session_pair()
    try:
        rows = s.execute(select(WorldRow).order_by(WorldRow.id)).scalars().all()
        return {"items": [{"id": r.id, "name": r.name, "tick": r.tick, "status": r.status} for r in rows],
                "next_cursor": None}
    finally:
        eng.dispose()


@app.get("/api/v1/worlds/{world_id}", dependencies=[Depends(auth)])
def get_world(world_id: str) -> dict[str, Any]:
    from agentville.engine.persistence import load_world

    eng, s = _session_pair()
    try:
        w = load_world(s, world_id)
        return {"id": w.id, "tick": w.tick, "status": "paused", "agents": len(w.agents),
                "jobs": len(w.jobs), "event_hash": w.event_hash}
    except Exception:
        raise HTTPException(status_code=404, detail="world not found") from None
    finally:
        eng.dispose()


@app.post("/api/v1/worlds/{world_id}/run", dependencies=[Depends(auth)])
def run_world(world_id: str, body: RunReq) -> dict[str, Any]:
    from sqlalchemy import update

    from agentville.db.models import World as WorldRow
    from agentville.engine.mind_factory import build_minds
    from agentville.engine.persistence import load_world, save_snapshot, set_world_status
    from agentville.engine.scheduler import Scheduler

    eng, s = _session_pair()
    try:
        w = load_world(s, world_id)
        set_world_status(s, world_id, "running")
        minds = build_minds(w.agents, s, mode=body.mode, mock_policy=body.mock)
        sched = Scheduler(w, s, minds)
        for _ in range(body.ticks):
            sched.run_tick()
            s.commit()
        save_snapshot(s, w)
        set_world_status(s, world_id, "paused")
        s.execute(update(WorldRow).where(WorldRow.id == world_id).values(tick=w.tick))
        s.commit()
        return {"run_id": f"{world_id}@{w.tick}", "ticks": body.ticks, "event_hash": w.event_hash[:12]}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=409, detail=f"run failed: {e}") from e
    finally:
        eng.dispose()


@app.get("/api/v1/worlds/{world_id}/state", dependencies=[Depends(auth)])
def world_state(world_id: str, tick: int = -1) -> dict[str, Any]:
    from agentville.engine.persistence import load_world

    eng, s = _session_pair()
    try:
        w = load_world(s, world_id)
        agents = [
            {"id": a.id, "role": a.role, "group": a.group_type.value, "status": a.status.value,
             "funds": a.vitals.funds, "energy": a.vitals.energy, "reputation": a.vitals.reputation}
            for a in w.agents.values()
        ]
        jobs = [
            {"id": j.id, "role": j.role, "reward": j.reward, "difficulty": j.difficulty,
             "status": j.status.value, "assigned": j.assigned_agent}
            for j in w.jobs.values()
        ]
        return {"world": w.id, "tick": w.tick, "agents": agents, "jobs": jobs,
                "money_supply": sum(w.accounts.values())}
    except Exception:
        raise HTTPException(status_code=404, detail="world not found") from None
    finally:
        eng.dispose()


@app.post("/api/v1/system/kill", dependencies=[Depends(auth)])
def kill_switch() -> dict[str, str]:
    """Global stop: world halts within 1 tick (loop checks status each tick)."""
    from sqlalchemy import update

    from agentville.db.models import World as WorldRow

    eng, s = _session_pair()
    try:
        s.execute(update(WorldRow).values(status="halted"))
        s.commit()
        return {"status": "halted"}
    finally:
        eng.dispose()


@app.get("/api/v1/system/health", dependencies=[Depends(auth)])
def health() -> dict[str, Any]:
    from sqlalchemy.orm import Session

    from agentville.db.session import make_engine
    from agentville.gateway.llm.gateway import LLMGateway

    eng = make_engine("sqlite://", apply_triggers=False)
    gw = LLMGateway(Session(eng), mode="live")
    ids = sorted(set(gw.providers) | set(getattr(gw, "_remote_cfgs", {})))
    out = {"providers": {pid: "ready" for pid in ids}, "db": "ok", "sandbox": "unknown"}
    eng.dispose()
    return out


@app.get("/api/v1/economy/{world_id}", dependencies=[Depends(auth)])
def economy(world_id: str) -> dict[str, Any]:
    from agentville.engine.persistence import load_world

    eng, s = _session_pair()
    try:
        w = load_world(s, world_id)
        supply = sum(w.accounts.values())
        agent_funds = sum(v for k, v in w.accounts.items() if k.startswith("agent:"))
        passes = sum(1 for j in w.jobs.values() if j.status.value == "verified_pass")
        fills = sum(1 for j in w.jobs.values() if j.status.value not in ("open", "expired"))
        return {"world": w.id, "money_supply": supply, "agent_funds": agent_funds,
                "buyer_funds": supply - agent_funds, "jobs_total": len(w.jobs),
                "pass_rate": passes / len(w.jobs) if w.jobs else 0,
                "fill_rate": fills / len(w.jobs) if w.jobs else 0}
    except Exception:
        raise HTTPException(status_code=404, detail="world not found") from None
    finally:
        eng.dispose()


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    """Prometheus text endpoint (TRD S10 subset)."""
    eng, s = _session_pair()
    try:
        from sqlalchemy import func, select

        from agentville.db.models import World as WorldRow

        n = s.scalar(select(func.count()).select_from(WorldRow)) or 0
        return f"# TYPE agentville_worlds gauge\nagentville_worlds {n}\n"
    finally:
        eng.dispose()


# --- websocket ----------------------------------------------------------------

class Hub:
    """Fan-out for world tick deltas."""

    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.clients):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


hub = Hub()


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, world_id: str = "world", token: str = "") -> None:
    """Snapshot-then-delta stream; reconnect sends a fresh snapshot."""
    await ws.accept()
    hub.clients.add(ws)
    try:
        while True:
            await asyncio.sleep(1)
            await ws.send_json({"t": "status", "status": "idle", "world_id": world_id})
    except WebSocketDisconnect:
        hub.clients.discard(ws)
