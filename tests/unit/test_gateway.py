"""T1.5: gateway validation pipeline, strike classification, handlers (TRD S3.6/S3.7)."""

from __future__ import annotations

from agentville.config import load_economy
from agentville.engine.events import EventLog
from agentville.engine.jobs import JobTemplate
from agentville.engine.ledger import LedgerWriter
from agentville.engine.types import ActionResult, AgentState, GroupType, Proposal, Vitals
from agentville.engine.world import World
from agentville.gateway.actions.handlers.basic import build_handlers
from agentville.gateway.actions.validator import execute, idempotency_key


class _Rng:
    def choice(self, seq):  # noqa: ANN001, ANN202
        return seq[0]

    def sample(self, seq, k):  # noqa: ANN001, ANN202
        return list(seq)[:k]

    def randint(self, a, b):  # noqa: ANN001, ANN202
        return a


def _mk(seed: int = 11) -> tuple[World, AgentState, LedgerWriter, EventLog]:
    eco = load_economy()
    w = World(id="w1", name="t", seed=seed, preset="small_city", economy=eco)
    agent = AgentState(
        id="agent_000000", world_id="w1", role="content_creator", group_type=GroupType.LEARNER,
        vitals=Vitals(energy=100, funds=500, reputation=50.0),
    )
    w.agents[agent.id] = agent
    led = LedgerWriter(_session(), world_id="w1")
    # fund through the ledger (double-entry guard rejects debits without credit history)
    led.post(tick=0, debit="treasury_mint", credit="treasury", amount=10_000, reason="seed")
    led.post(tick=0, debit="treasury", credit=f"agent:{agent.id}", amount=500, reason="starting_funds")
    w.accounts[f"agent:{agent.id}"] = 500
    for i in range(3):
        w.accounts[f"buyer:b{i}"] = 5_000
    job = JobTemplate.make(_Rng(), 1, "job_000001", "b1", 0, eco.deadline_ticks, eco.job_rewards[1])
    w.jobs[job.id] = job
    return w, agent, led, EventLog(_session())



from sqlalchemy.orm import Session  # noqa: E402

from agentville.db.session import make_engine  # noqa: E402

_ENGINE = None


def _session() -> Session:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = make_engine("sqlite://", apply_triggers=True)
    return Session(_ENGINE)


def _close_sessions() -> None:
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.dispose()
        _ENGINE = None


# NOTE: handlers only use ledger/events via the gateway; a single module-level
# in-memory engine per test process keeps these tests fast and isolated enough.


def test_take_job_happy_path() -> None:
    w, agent, led, ev = _mk()
    r = execute(w, agent, Proposal(action="take_job", args={"job_id": "job_000001"}), led, ev, set(), build_handlers())
    assert r.status == "accepted"
    assert w.jobs["job_000001"].status == "taken"
    assert agent.current_job_id == "job_000001"
    assert agent.vitals.energy == 98  # take_job costs 2


def test_take_job_i7_concurrency_cap() -> None:
    w, agent, led, ev = _mk()
    eco = w.economy
    assert eco is not None
    for i in range(eco.max_concurrent_jobs + 1):
        job = JobTemplate.make(_Rng(), 1, f"job_c{i}", "b1", 0, eco.deadline_ticks, 40)
        w.jobs[job.id] = job
        execute(w, agent, Proposal(action="take_job", args={"job_id": job.id}), led, ev, set(), build_handlers())
    taken = [j for j in w.jobs.values() if j.assigned_agent == agent.id and j.status == "taken"]
    assert len(taken) == eco.max_concurrent_jobs


def test_unknown_action_is_strike() -> None:
    w, agent, led, ev = _mk()
    r = execute(w, agent, Proposal(action="set_balance", args={}), led, ev, set(), build_handlers())
    assert r.status == "rejected"
    assert agent.vitals.strikes == 1
    assert r.reject_reason and "unknown action" in r.reject_reason


def test_bad_schema_is_strike() -> None:
    w, agent, led, ev = _mk()
    r = execute(w, agent, Proposal(action="write_note", args={"text": "x" * 500, "importance": 9}), led, ev, set(), build_handlers())
    assert r.status == "rejected"
    assert agent.vitals.strikes == 1


def test_precondition_no_strike() -> None:
    w, agent, led, ev = _mk()
    agent.vitals.energy = 1
    r = execute(w, agent, Proposal(action="take_job", args={"job_id": "job_000001"}), led, ev, set(), build_handlers())
    assert r.status == "rejected"
    assert agent.vitals.strikes == 0  # PreconditionFailed never strikes


def test_role_mismatch_no_strike() -> None:
    w, agent, led, ev = _mk()
    agent.role = "developer"
    r = execute(w, agent, Proposal(action="take_job", args={"job_id": "job_000001"}), led, ev, set(), build_handlers())
    assert r.status == "rejected" and agent.vitals.strikes == 0


def test_idempotency_blocks_duplicate() -> None:
    w, agent, led, ev = _mk()
    seen: set[str] = set()
    r1 = execute(w, agent, Proposal(action="write_note", args={"text": "hi", "importance": 1}), led, ev, seen, build_handlers())
    r2 = execute(w, agent, Proposal(action="write_note", args={"text": "hi", "importance": 1}), led, ev, seen, build_handlers())
    assert r1.status == "accepted" and r2.status == "rejected"
    assert "duplicate" in (r2.reject_reason or "")


def test_idempotency_key_differs_by_args() -> None:
    assert idempotency_key("a", 1, "noop", {}) != idempotency_key("a", 1, "noop", {"x": 1})
    assert idempotency_key("a", 1, "noop", {}) == idempotency_key("a", 1, "noop", {})


def test_work_on_effort_energy_math() -> None:
    w, agent, led, ev = _mk()
    execute(w, agent, Proposal(action="take_job", args={"job_id": "job_000001"}), led, ev, set(), build_handlers())
    e0 = agent.vitals.energy
    r = execute(w, agent, Proposal(action="work_on", args={"job_id": "job_000001", "effort": 3}), led, ev, set(), build_handlers())
    assert r.status == "accepted"
    assert agent.vitals.energy == e0 - 15  # 5 per effort


def test_buy_item_moves_coins() -> None:
    w, agent, led, ev = _mk()
    eco = w.economy
    assert eco is not None
    item = eco.market_items[0]
    r = execute(w, agent, Proposal(action="buy_item", args={"item_id": item.id}), led, ev, set(), build_handlers())
    assert r.status == "accepted" and r.coin_delta == -item.price
    assert agent.vitals.funds == 500 - item.price
    assert agent.inventory.get(item.id) == 1


def test_buy_unknown_item_strike() -> None:
    w, agent, led, ev = _mk()
    r = execute(w, agent, Proposal(action="buy_item", args={"item_id": "nope"}), led, ev, set(), build_handlers())
    assert r.status == "rejected" and agent.vitals.strikes == 1


def test_rest_and_eat() -> None:
    w, agent, led, ev = _mk()
    agent.vitals.energy = 50
    r = execute(w, agent, Proposal(action="rest", args={}), led, ev, set(), build_handlers())
    assert agent.vitals.energy == 80 and r.energy_cost == -30
    f0 = agent.vitals.funds
    r = execute(w, agent, Proposal(action="eat", args={}), led, ev, set(), build_handlers())
    assert agent.vitals.funds == f0 - 10


def test_quit_job_opens_and_penalizes_rep() -> None:
    w, agent, led, ev = _mk()
    execute(w, agent, Proposal(action="take_job", args={"job_id": "job_000001"}), led, ev, set(), build_handlers())
    agent.vitals.reputation = 50.0
    r = execute(w, agent, Proposal(action="quit_job", args={"job_id": "job_000001"}), led, ev, set(), build_handlers())
    assert r.status == "accepted"
    assert w.jobs["job_000001"].status == "open" and w.jobs["job_000001"].assigned_agent is None
    assert agent.vitals.reputation == 45.0


def test_submit_requires_taken_state() -> None:
    w, agent, led, ev = _mk()
    r = execute(w, agent, Proposal(action="submit_work", args={"job_id": "job_000001", "artifact_id": "a1"}), led, ev, set(), build_handlers())
    assert r.status == "rejected" and agent.vitals.strikes == 0  # precondition, not fault


def test_fail_closed_on_handler_crash() -> None:
    w, agent, led, ev = _mk()

    class Boom:
        spec = None

        def validate(self, ctx, args):  # noqa: ANN001, ANN202
            raise RuntimeError("boom")

        def execute(self, ctx, args):  # noqa: ANN001, ANN202
            return ActionResult(status="accepted", observation="never")

    handlers = {"noop": Boom()}
    r = execute(w, agent, Proposal(action="noop", args={}), led, ev, set(), handlers)
    assert r.status == "error"
    assert "boom" in (r.reject_reason or "")
