"""Lifecycle: per-tick costs, vitals dynamics, death rules (TRD S3.5, AGENT_ROLES S4-S5)."""

from __future__ import annotations

from dataclasses import dataclass

from agentville.engine.events import EventLog
from agentville.engine.jobs import JobBoard, JobStatus
from agentville.engine.ledger import LedgerWriter
from agentville.engine.types import AgentState, AgentStatus
from agentville.engine.world import World


@dataclass
class Death:
    """A death record produced by check_deaths."""

    agent_id: str
    cause: str
    tick: int


def apply_costs(
    world: World,
    ledger: LedgerWriter,
    events: EventLog,
    *,
    acted: set[str],
    ate: set[str],
) -> None:
    """Rent always; food per auto_eat rule; idle regen; unpaid-cost accounting.

    auto_eat=false (docs default): food is paid via the eat action; skipping food
    costs 20 energy that tick. Rent unpaid -> partial pay + negative_funds_ticks++.
    """
    eco = world.economy
    rent = eco.rent_per_tick if eco else 20
    food = eco.food_per_tick if eco else 10
    idle_regen = eco.energy.idle_regen if eco else 5
    for agent in world.alive_agents():
        _charge(world, ledger, events, agent, rent, "landlord", "rent")
        if eco is not None and eco.auto_eat:
            _charge(world, ledger, events, agent, food, "market", "food")
        elif agent.id not in ate:
            agent.vitals.energy = max(0, agent.vitals.energy - 20)
        if agent.vitals.energy == 0:
            agent.low_energy_ticks += 1
        else:
            agent.low_energy_ticks = 0
        if agent.id not in acted:
            agent.vitals.energy = min(100, agent.vitals.energy + idle_regen)


def _charge(
    world: World, ledger: LedgerWriter, events: EventLog, agent: AgentState, amount: int, to: str, reason: str
) -> None:
    """Pay what's possible; unpaid remainder increments negative_funds_ticks (I2-safe)."""
    account = f"agent:{agent.id}"
    balance = world.accounts.get(account, 0)
    paid = min(balance, amount)
    if paid > 0:
        ledger.post(tick=world.tick, debit=account, credit=to, amount=paid, reason=reason)
        world.accounts[account] = balance - paid
        agent.vitals.funds = world.accounts[account]
    if paid < amount:
        agent.negative_funds_ticks += 1
    events.emit(
        world.id, tick=world.tick, type_="cost_applied", agent_id=agent.id,
        payload={reason: paid, "unpaid": amount - paid},
    )


def check_deaths(world: World, tick: int) -> list[Death]:
    """Evaluate death conditions end of tick, first match wins; 5-tick onboarding grace."""
    deaths: list[Death] = []
    for agent in world.alive_agents():
        if tick - agent.born_tick < 5:
            continue  # onboarding grace (AGENT_ROLES S5)
        cause = _death_cause(agent)
        if cause is not None:
            kill(world, agent, tick, cause)
            deaths.append(Death(agent_id=agent.id, cause=cause, tick=tick))
    return deaths


def _death_cause(agent: AgentState) -> str | None:
    """First matching death condition, in doc order."""
    if agent.negative_funds_ticks >= 2:
        return "bankruptcy"
    if agent.low_energy_ticks >= 3:
        return "exhaustion"
    if agent.vitals.strikes > 10:
        return "misconduct"
    if agent.idle_ticks >= 30:
        return "unemployment"
    if agent.vitals.reputation <= 0:
        return "blacklisted"
    return None


def kill(world: World, agent: AgentState, tick: int, cause: str) -> None:
    """Mark dead; release an assigned TAKEN job back to OPEN with no penalty (TRD S3.5)."""
    agent.status = AgentStatus.DEAD
    if agent.current_job_id:
        job = world.jobs.get(agent.current_job_id)
        if job is not None and job.status == JobStatus.TAKEN:
            JobBoard(world).transition(job.id, JobStatus.OPEN)
            job.assigned_agent = None
        agent.current_job_id = None
