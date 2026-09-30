"""V1 handlers. LLM/sandbox-dependent effects are stubbed until Phases 2-3 (T1.5 scope)."""

from __future__ import annotations

from typing import Any

from agentville.engine.jobs import JobBoard, JobStatus
from agentville.engine.types import ActionResult
from agentville.gateway.actions.base import ActionContext, PreconditionFailed, ValidationError
from agentville.gateway.actions.registry import (
    BuyItemArgs,
    EmptyArgs,
    QuitJobArgs,
    SubmitWorkArgs,
    TakeJobArgs,
    UpdatePlaybookArgs,
    WorkOnArgs,
    WriteNoteArgs,
)
from agentville.gateway.actions.validator import take_job_guard


def _job_or_fail(ctx: ActionContext, job_id: str, *, statuses: tuple[JobStatus, ...]) -> Any:
    job = ctx.world.jobs.get(job_id)
    if job is None:
        raise PreconditionFailed(f"job {job_id} not found")
    if job.status not in statuses:
        raise PreconditionFailed(f"job {job_id} in state {job.status}, expected one of {statuses}")
    return job


class TakeJob:
    """Assign an OPEN job (role/rep/concurrency checks in take_job_guard)."""

    spec = None  # filled by build_handlers

    def validate(self, ctx: ActionContext, args: TakeJobArgs) -> None:
        take_job_guard(ctx.world, ctx.agent, JobBoard(ctx.world), args.job_id)

    def execute(self, ctx: ActionContext, args: TakeJobArgs) -> ActionResult:
        job = take_job_guard(ctx.world, ctx.agent, JobBoard(ctx.world), args.job_id)
        JobBoard(ctx.world).transition(job.id, JobStatus.TAKEN)
        job.assigned_agent = ctx.agent.id
        ctx.agent.current_job_id = job.id
        ctx.events.emit(ctx.world.id, tick=ctx.tick, type_="job_taken", agent_id=ctx.agent.id, payload={"job_id": job.id})
        return ActionResult(status="accepted", observation=f"took job {job.id} ({job.title})")


class WorkOn:
    """Add progress; artifact production is an LLM call stubbed until Phase 2."""

    spec = None

    def validate(self, ctx: ActionContext, args: WorkOnArgs) -> None:
        job = _job_or_fail(ctx, args.job_id, statuses=(JobStatus.TAKEN,))
        if job.assigned_agent != ctx.agent.id:
            raise ValidationError("cannot work on another agent's job")

    def execute(self, ctx: ActionContext, args: WorkOnArgs) -> ActionResult:
        job = _job_or_fail(ctx, args.job_id, statuses=(JobStatus.TAKEN,))
        ctx.events.emit(
            ctx.world.id, tick=ctx.tick, type_="work_progress", agent_id=ctx.agent.id,
            payload={"job_id": job.id, "effort": args.effort},
        )
        stub = "draft produced (LLM stubbed until Phase 2)"
        return ActionResult(status="accepted", observation=f"worked on {job.id}: {stub}")


class SubmitWork:
    """TAKEN -> SUBMITTED and queue verification (verifier lands in Phase 3)."""

    spec = None

    def validate(self, ctx: ActionContext, args: SubmitWorkArgs) -> None:
        job = _job_or_fail(ctx, args.job_id, statuses=(JobStatus.TAKEN,))
        if job.assigned_agent != ctx.agent.id:
            raise ValidationError("cannot submit another agent's job")

    def execute(self, ctx: ActionContext, args: SubmitWorkArgs) -> ActionResult:
        job = _job_or_fail(ctx, args.job_id, statuses=(JobStatus.TAKEN,))
        JobBoard(ctx.world).transition(job.id, JobStatus.SUBMITTED)
        ctx.events.emit(
            ctx.world.id, tick=ctx.tick, type_="work_submitted", agent_id=ctx.agent.id,
            payload={"job_id": job.id, "artifact_id": args.artifact_id},
        )
        return ActionResult(status="accepted", observation=f"submitted {job.id} for verification")


class WriteNote:
    """Append a notebook entry (cap 50: oldest archived in Phase 2)."""

    spec = None

    def validate(self, ctx: ActionContext, args: WriteNoteArgs) -> None:
        return

    def execute(self, ctx: ActionContext, args: WriteNoteArgs) -> ActionResult:
        notes = ctx.extras.setdefault("notes", {})
        lst = notes.setdefault(ctx.agent.id, [])
        lst.append({"tick": ctx.tick, "text": args.text, "importance": args.importance})
        ctx.events.emit(
            ctx.world.id, tick=ctx.tick, type_="note_written", agent_id=ctx.agent.id,
            payload={"note_id": len(lst), "importance": args.importance},
        )
        return ActionResult(status="accepted", observation="note saved")


class UpdatePlaybook:
    """New version; full evidence validation lands in Phase 4 (T4.1)."""

    spec = None

    def validate(self, ctx: ActionContext, args: UpdatePlaybookArgs) -> None:
        if not args.body_md.strip():
            raise ValidationError("empty playbook")

    def execute(self, ctx: ActionContext, args: UpdatePlaybookArgs) -> ActionResult:
        pbs = ctx.extras.setdefault("playbooks", {})
        versions = pbs.setdefault(ctx.agent.id, [])
        versions.append({"version": len(versions) + 1, "tick": ctx.tick, "body_md": args.body_md})
        ctx.events.emit(
            ctx.world.id, tick=ctx.tick, type_="playbook_updated", agent_id=ctx.agent.id,
            payload={"version": len(versions)},
        )
        return ActionResult(status="accepted", observation=f"playbook v{len(versions)} saved")


class BuyItem:
    """Purchase from catalog; effect application matures in Phase 4 (T4.5)."""

    spec = None

    def validate(self, ctx: ActionContext, args: BuyItemArgs) -> None:
        eco = ctx.world.economy
        catalog = {i.id: i for i in (eco.market_items if eco else [])}
        if args.item_id not in catalog:
            raise ValidationError(f"unknown item {args.item_id}")
        item = catalog[args.item_id]
        if ctx.agent.vitals.funds < item.price:
            raise PreconditionFailed(f"item costs {item.price}, funds {ctx.agent.vitals.funds}")

    def execute(self, ctx: ActionContext, args: BuyItemArgs) -> ActionResult:
        eco = ctx.world.economy
        assert eco is not None
        item = {i.id: i for i in eco.market_items}[args.item_id]
        ctx.ledger.post(
            tick=ctx.tick, debit=f"agent:{ctx.agent.id}", credit="market",
            amount=item.price, reason="item_purchase", ref_type="market_item", ref_id=item.id,
        )
        ctx.world.accounts[f"agent:{ctx.agent.id}"] = ctx.world.accounts.get(f"agent:{ctx.agent.id}", 0) - item.price
        ctx.agent.vitals.funds -= item.price
        ctx.agent.inventory[item.id] = ctx.agent.inventory.get(item.id, 0) + 1
        ctx.events.emit(
            ctx.world.id, tick=ctx.tick, type_="item_bought", agent_id=ctx.agent.id,
            payload={"item_id": item.id, "price": item.price},
        )
        return ActionResult(status="accepted", coin_delta=-item.price, observation=f"bought {item.id}")


class Rest:
    spec = None

    def validate(self, ctx: ActionContext, args: EmptyArgs) -> None:
        return

    def execute(self, ctx: ActionContext, args: EmptyArgs) -> ActionResult:
        eco = ctx.world.economy
        gain = eco.energy.rest_gain if eco else 30
        ctx.agent.vitals.energy = min(100, ctx.agent.vitals.energy + gain)
        return ActionResult(status="accepted", energy_cost=-gain, observation=f"rested +{gain} energy")


class Eat:
    spec = None

    def validate(self, ctx: ActionContext, args: EmptyArgs) -> None:
        eco = ctx.world.economy
        cost = eco.food_per_tick if eco else 10
        if ctx.agent.vitals.funds < cost:
            raise PreconditionFailed(f"food costs {cost}, funds {ctx.agent.vitals.funds}")

    def execute(self, ctx: ActionContext, args: EmptyArgs) -> ActionResult:
        eco = ctx.world.economy
        cost = eco.food_per_tick if eco else 10
        ctx.ledger.post(
            tick=ctx.tick, debit=f"agent:{ctx.agent.id}", credit="market",
            amount=cost, reason="food",
        )
        ctx.world.accounts[f"agent:{ctx.agent.id}"] = ctx.world.accounts.get(f"agent:{ctx.agent.id}", 0) - cost
        ctx.agent.vitals.funds -= cost
        return ActionResult(status="accepted", coin_delta=-cost, observation=f"ate for {cost}")


class QuitJob:
    spec = None

    def validate(self, ctx: ActionContext, args: QuitJobArgs) -> None:
        job = _job_or_fail(ctx, args.job_id, statuses=(JobStatus.TAKEN,))
        if job.assigned_agent != ctx.agent.id:
            raise ValidationError("cannot quit another agent's job")

    def execute(self, ctx: ActionContext, args: QuitJobArgs) -> ActionResult:
        job = ctx.world.jobs[args.job_id]
        JobBoard(ctx.world).transition(job.id, JobStatus.OPEN)
        job.assigned_agent = None
        ctx.agent.current_job_id = None
        ctx.agent.vitals.reputation = max(0.0, ctx.agent.vitals.reputation - 5)
        ctx.events.emit(
            ctx.world.id, tick=ctx.tick, type_="job_quit", agent_id=ctx.agent.id,
            payload={"job_id": job.id},
        )
        return ActionResult(status="accepted", observation=f"quit {job.id} (-5 reputation)")


class Noop:
    spec = None

    def validate(self, ctx: ActionContext, args: EmptyArgs) -> None:
        return

    def execute(self, ctx: ActionContext, args: EmptyArgs) -> ActionResult:
        return ActionResult(status="accepted", observation="did nothing")


# LLM/sandbox/study stubs: same interface; real behavior in later phases
class StubLLMAction:
    """Placeholder for save_skill/run_skill/study_web/request_exam until Phases 2-3/7."""

    spec = None

    def __init__(self, name: str, note: str) -> None:
        self.name = name
        self.note = note

    def validate(self, ctx: ActionContext, args: Any) -> None:
        return

    def execute(self, ctx: ActionContext, args: Any) -> ActionResult:
        return ActionResult(status="accepted", observation=f"{self.name}: {self.note}")


def build_handlers() -> dict[str, Any]:
    """Action name -> handler instance (T1.5; stubs where later phases land)."""
    handlers: dict[str, Any] = {
        "take_job": TakeJob(),
        "work_on": WorkOn(),
        "submit_work": SubmitWork(),
        "write_note": WriteNote(),
        "update_playbook": UpdatePlaybook(),
        "buy_item": BuyItem(),
        "rest": Rest(),
        "eat": Eat(),
        "quit_job": QuitJob(),
        "noop": Noop(),
    }
    for name, note in (
        ("save_skill", "sandbox arrives in Phase 3 (T3.1); accepted as no-op for now"),
        ("run_skill", "sandbox arrives in Phase 3; accepted as no-op for now"),
        ("study_web", "web gateway arrives in Phase 7 (T7.1); accepted as no-op for now"),
        ("request_exam", "exams arrive in Phase 7 (T7.6); accepted as no-op for now"),
    ):
        handlers[name] = StubLLMAction(name, note)
    return handlers
