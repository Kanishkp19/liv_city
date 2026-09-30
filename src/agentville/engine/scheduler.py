"""Tick scheduler (TRD S4): the authoritative 10-step loop, P1 offline mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from agentville.engine.events import EventLog
from agentville.engine.jobs import JobBoard, JobGenerator, JobStatus
from agentville.engine.ledger import LedgerWriter
from agentville.engine.lifecycle import apply_costs, check_deaths
from agentville.engine.mocks import MockMind, mock_artifact
from agentville.engine.types import AgentStatus, Proposal
from agentville.engine.world import World
from agentville.gateway.actions.handlers.basic import build_handlers
from agentville.gateway.actions.validator import execute
from agentville.rng import derive_rng


@dataclass
class TickReport:
    """Per-tick summary for logs/CLI."""

    tick: int
    actions: int = 0
    rejections: int = 0
    jobs_generated: int = 0
    submissions: int = 0
    passes: int = 0
    payout_total: int = 0
    deaths: list[str] = field(default_factory=list)
    event_hash: str = ""


class Scheduler:
    """Drives one world; minds map agent_id -> object with decide()."""

    def __init__(self, world: World, session: Session, minds: dict[str, Any] | None = None) -> None:
        from agentville.engine.persistence import create_world as _noop  # noqa: F401

        self.world = world
        self.session = session
        self.minds = minds or {}
        self.ledger = LedgerWriter(session, world_id=world.id)
        self.events = EventLog(session)
        self.board = JobBoard(world)
        self.generator = JobGenerator(world)
        self.    handlers = build_handlers()
        self.verifier = VerifierServiceP1()
        self.seen_keys: set[str] = set()
        self.reports: list[TickReport] = []
        self._pending_submissions: list[tuple[str, Proposal]] = []
        self._seeded_economy = False

    def _ensure_economy_seeded(self) -> None:
        if not self._seeded_economy:
            from agentville.engine.market import seed_companies_and_buyers

            seed_companies_and_buyers(self.world, self.ledger, self.events, session=self.session)
            # mirror agent starting_funds into the ledger (mint-sourced, logged once)
            for aid in self.world.agents:
                acct = f"agent:{aid}"
                want = self.world.accounts.get(acct, 0)
                have = self.ledger.balance(acct)
                if want > have:
                    self.ledger.post(
                        tick=self.world.tick, debit="treasury_mint", credit=acct,
                        amount=want - have, reason="starting_funds",
                    )
                    self.events.emit(
                        self.world.id, tick=self.world.tick, type_="starting_funds",
                        agent_id=aid, payload={"amount": want - have},
                    )
            self._seeded_economy = True

    def run_tick(self) -> TickReport:
        """One authoritative tick; DB transaction per tick, rollback on LedgerError."""
        w = self.world
        w.tick += 1
        t = w.tick
        report = TickReport(tick=t)
        self._ensure_economy_seeded()
        self.events.emit(w.id, tick=t, type_="tick_started", agent_id=None, payload={"tick": t})

        # expire past-deadline jobs (grace from economy)
        eco = w.economy
        grace = eco.late_grace_ticks if eco else 1
        expired = self.board.expire_past_deadline(t, grace, eco.late_multiplier if eco else 0.7)
        for job in expired:
            if job.assigned_agent:
                agent = w.agents.get(job.assigned_agent)
                if agent is not None:
                    agent.current_job_id = None
                    rep_delta = eco.reputation_delta.get("expired", -8) if eco else -8
                    agent.vitals.reputation = max(0.0, agent.vitals.reputation + rep_delta)

        # generate + post new jobs
        for job in self.generator.generate(t):
            w.jobs[job.id] = job
            report.jobs_generated += 1
            self.events.emit(
                w.id, tick=t, type_="job_posted", agent_id=None,
                payload={"job_id": job.id, "role": job.role, "reward": job.reward, "deadline": job.deadline_tick},
            )
        from agentville.engine.persistence import sync_jobs

        sync_jobs(self.session, w)  # DB rows before verifications reference them

        # decide (concurrently with LLM in P2; sequential mock here) in seeded order
        order = [a.id for a in w.alive_agents()]
        rng = derive_rng(w.seed, t, "order")
        rng.shuffle(order)
        proposals: dict[str, Proposal] = {}
        acted: set[str] = set()
        ate: set[str] = set()
        for aid in order:
            agent = w.agents[aid]
            mind = self.minds.get(aid, MockMind("noop"))
            try:
                proposals[aid] = mind.decide(w, agent)
            except Exception:  # fail closed: skip as noop (no strike)
                proposals[aid] = Proposal(action="noop", reason="decision error")
                self.events.emit(w.id, tick=t, type_="agent_decision_skipped", agent_id=aid, payload={"reason": "error"})

        # apply sequentially in seeded order
        for aid in order:
            agent = w.agents.get(aid)
            if agent is None or agent.status != AgentStatus.ALIVE:
                continue
            proposal = proposals.get(aid, Proposal(action="noop"))
            if proposal.action != "noop":
                acted.add(aid)
            if proposal.action == "eat":
                ate.add(aid)
            result = execute(w, agent, proposal, self.ledger, self.events, self.seen_keys, self.handlers)
            report.actions += 1
            if result.status != "accepted":
                report.rejections += 1
            # oracle-style artifact capture on submit: mock verifier needs an artifact
            if proposal.action == "submit_work" and result.status == "accepted":
                self._pending_submissions.append((aid, proposal))

        # verify submissions (P1: mock service on stored artifacts)
        for aid, proposal in self._pending_submissions:
            self._verify_submission(aid, proposal, report, eco)
        self._pending_submissions = []

        # costs + deaths
        apply_costs(w, self.ledger, self.events, acted=acted, ate=ate)
        for death in check_deaths(w, t):
            report.deaths.append(f"{death.agent_id}:{death.cause}")
            self.events.emit(w.id, tick=t, type_="agent_died", agent_id=death.agent_id, payload={"cause": death.cause})
            self.minds.pop(death.agent_id, None)

        # reconcile + snapshot + commit hash
        self.ledger.reconcile(w.id)
        from agentville.engine.persistence import save_snapshot, sync_agents

        sync_agents(self.session, w)
        save_snapshot(self.session, w)
        head = self.events.head(w.id)
        w.event_hash = head
        report.event_hash = head
        self.events.emit(w.id, tick=t, type_="tick_committed", agent_id=None, payload={"event_hash": head})
        self.reports.append(report)
        return report

    def _verify_submission(self, aid: str, proposal: Proposal, report: TickReport, eco: Any) -> None:
        """Verify one submitted job and settle payment (extracted for typing clarity)."""
        w = self.world
        agent = w.agents.get(aid)
        submitted_id = str(proposal.args.get("job_id", ""))
        submitted = w.jobs.get(submitted_id)
        if agent is None or submitted is None or submitted.status != JobStatus.SUBMITTED:
            return
        artifact = mock_artifact(f"{w.seed}:{submitted.id}", submitted.role, submitted.params)
        vres = self.verifier.verify(submitted, artifact)
        report.submissions += 1
        target = JobStatus.VERIFIED_PASS if vres.passed else JobStatus.VERIFIED_FAIL
        self.board.transition(submitted.id, target)
        if vres.passed:
            report.passes += 1
            from agentville.verifier.service import settle_payment

            payout = settle_payment(
                w, self.ledger, self.events, submitted, vres,
                late=False, late_multiplier=eco.late_multiplier if eco else 0.7,
                rep_deltas=eco.reputation_delta if eco else {}, session=self.session,
            )
            report.payout_total += payout
            agent.vitals.funds += payout
        else:
            rep_delta = eco.reputation_delta.get("fail", -5) if eco else -5
            agent.vitals.reputation = max(0.0, agent.vitals.reputation + rep_delta)
        agent.current_job_id = None


from agentville.verifier.service import VerifierService  # noqa: E402


class VerifierServiceP1(VerifierService):
    """P1 alias: same service; mock artifacts are crafted to pass."""

    pass
