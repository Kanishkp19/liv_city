"""ORM models mirroring BACKEND_SCHEMA.md S1 exactly.

Money is integer coins. Events and ledger are append-only (enforced by triggers in
triggers.py). Timestamps are ISO-8601 UTC strings; tick is the simulation clock.
"""

from __future__ import annotations

from sqlalchemy import (
    REAL as Real,
)
from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from agentville.db.base import Base


class World(Base):
    __tablename__ = "worlds"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str]
    seed: Mapped[int]
    preset: Mapped[str]
    tick: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="created")
    mode: Mapped[str] = mapped_column(default="live")
    source_world_id: Mapped[str | None] = mapped_column(ForeignKey("worlds.id"), nullable=True)
    config_json: Mapped[str]
    event_hash: Mapped[str] = mapped_column(default="")
    created_at: Mapped[str]


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    world_id: Mapped[str] = mapped_column(ForeignKey("worlds.id"))
    role: Mapped[str]
    generation: Mapped[int] = mapped_column(default=1)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    group_type: Mapped[str]
    status: Mapped[str] = mapped_column(default="alive")
    born_tick: Mapped[int]
    died_tick: Mapped[int | None] = mapped_column(nullable=True)
    death_cause: Mapped[str | None] = mapped_column(nullable=True)
    model_pref: Mapped[str | None] = mapped_column(nullable=True)
    name: Mapped[str]
    persona_seed: Mapped[str | None] = mapped_column(nullable=True)
    location: Mapped[str] = mapped_column(default="housing")
    current_job_id: Mapped[str | None] = mapped_column(nullable=True)
    inventory_json: Mapped[str] = mapped_column(default="{}")
    idle_ticks: Mapped[int] = mapped_column(default=0)
    low_energy_ticks: Mapped[int] = mapped_column(default=0)
    negative_funds_ticks: Mapped[int] = mapped_column(default=0)


Index("ix_agents_world_status", Agent.world_id, Agent.status)


class AgentVital(Base):
    __tablename__ = "agent_vitals"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), primary_key=True)
    tick: Mapped[int] = mapped_column(primary_key=True)
    energy: Mapped[int]
    funds: Mapped[int]
    reputation: Mapped[float]
    strikes: Mapped[int] = mapped_column(default=0)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str]
    tick: Mapped[int]
    debit_account: Mapped[str]
    credit_account: Mapped[str]
    amount: Mapped[int]
    reason: Mapped[str]
    ref_type: Mapped[str | None] = mapped_column(nullable=True)
    ref_id: Mapped[str | None] = mapped_column(nullable=True)
    event_id: Mapped[int | None] = mapped_column(nullable=True)


Index("ix_ledger_world_tick", LedgerEntry.world_id, LedgerEntry.tick)
Index("ix_ledger_debit", LedgerEntry.world_id, LedgerEntry.debit_account)
Index("ix_ledger_credit", LedgerEntry.world_id, LedgerEntry.credit_account)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    world_id: Mapped[str]
    name: Mapped[str]
    sector: Mapped[str]
    budget: Mapped[int]


class Buyer(Base):
    __tablename__ = "buyers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    world_id: Mapped[str]
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str]
    persona_json: Mapped[str]
    quality_bar: Mapped[float]
    roles_json: Mapped[str]


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    world_id: Mapped[str]
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyers.id"))
    role: Mapped[str]
    title: Mapped[str]
    brief: Mapped[str]
    params_json: Mapped[str]
    visible_params_json: Mapped[str]
    verifier_recipe_json: Mapped[str]
    reward: Mapped[int]
    penalty: Mapped[int] = mapped_column(default=0)
    difficulty: Mapped[int]
    min_reputation: Mapped[float] = mapped_column(Real, default=0)
    posted_tick: Mapped[int]
    deadline_tick: Mapped[int]
    status: Mapped[str] = mapped_column(default="open")
    assigned_agent: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    taken_tick: Mapped[int | None] = mapped_column(nullable=True)
    submitted_tick: Mapped[int | None] = mapped_column(nullable=True)
    payout: Mapped[int | None] = mapped_column(nullable=True)
    quality: Mapped[float | None] = mapped_column(nullable=True)
    is_audit_plant: Mapped[bool] = mapped_column(Boolean, default=False)


Index("ix_jobs_world_status", Job.world_id, Job.status, Job.role)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    world_id: Mapped[str]
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    tick: Mapped[int]
    kind: Mapped[str]
    path: Mapped[str]
    sha256: Mapped[str]
    size_bytes: Mapped[int]
    meta_json: Mapped[str] = mapped_column(default="{}")


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    world_id: Mapped[str]
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"))
    stage: Mapped[str]
    passed: Mapped[bool]
    score: Mapped[float | None] = mapped_column(nullable=True)
    details_json: Mapped[str]
    sandbox_run_id: Mapped[str | None] = mapped_column(nullable=True)
    tick: Mapped[int]
    error: Mapped[str | None] = mapped_column(nullable=True)


Index("ix_ver_job", Verification.job_id)


class JudgeVote(Base):
    __tablename__ = "judge_votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verification_id: Mapped[str] = mapped_column(ForeignKey("verifications.id"))
    model: Mapped[str]
    rubric_version: Mapped[str]
    score: Mapped[float]
    criteria_json: Mapped[str]
    rationale: Mapped[str | None] = mapped_column(nullable=True)
    llm_call_id: Mapped[int | None] = mapped_column(nullable=True)


class Event(Base):
    """Append-only source of truth; hash-chained (see events.py)."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str]
    tick: Mapped[int]
    seq: Mapped[int]
    type: Mapped[str]
    agent_id: Mapped[str | None] = mapped_column(nullable=True)
    payload_json: Mapped[str]
    cause_event_id: Mapped[int | None] = mapped_column(nullable=True)
    prev_hash: Mapped[str]
    hash: Mapped[str]

    __table_args__ = (UniqueConstraint("world_id", "tick", "seq", name="uq_events_world_tick_seq"),)


Index("ix_events_agent", Event.world_id, Event.agent_id, Event.tick)
Index("ix_events_type", Event.world_id, Event.type, Event.tick)


class SystemEvent(Base):
    """Non-transactional ops/errors; survives tick rollback."""

    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str | None] = mapped_column(nullable=True)
    tick: Mapped[int | None] = mapped_column(nullable=True)
    level: Mapped[str]
    message: Mapped[str]
    detail_json: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[str]


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    world_id: Mapped[str]
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    tick: Mapped[int]
    action: Mapped[str]
    args_json: Mapped[str]
    reason: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str]
    reject_reason: Mapped[str | None] = mapped_column(nullable=True)
    observation: Mapped[str | None] = mapped_column(nullable=True)
    energy_cost: Mapped[int] = mapped_column(default=0)
    coin_delta: Mapped[int] = mapped_column(default=0)
    idempotency_key: Mapped[str]
    llm_call_id: Mapped[int | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("world_id", "idempotency_key", name="uq_actions_world_idem"),
    )


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str | None] = mapped_column(nullable=True)
    tick: Mapped[int | None] = mapped_column(nullable=True)
    agent_id: Mapped[str | None] = mapped_column(nullable=True)
    purpose: Mapped[str]
    call_index: Mapped[int] = mapped_column(default=0)
    provider: Mapped[str | None] = mapped_column(nullable=True)
    model: Mapped[str | None] = mapped_column(nullable=True)
    prompt_hash: Mapped[str]
    prompt: Mapped[str]
    response: Mapped[str | None] = mapped_column(nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    repaired: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[str]


Index("ix_llm_world_tick", LLMCall.world_id, LLMCall.tick, LLMCall.agent_id, LLMCall.purpose)


class MemoryNote(Base):
    __tablename__ = "memory_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    tick: Mapped[int]
    text: Mapped[str]
    importance: Mapped[int]
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    version: Mapped[int]
    body_md: Mapped[str]
    tick: Mapped[int]
    score_at_save: Mapped[float | None] = mapped_column(nullable=True)

    __table_args__ = (UniqueConstraint("agent_id", "version", name="uq_playbooks_agent_version"),)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    name: Mapped[str]
    language: Mapped[str] = mapped_column(default="python")
    code: Mapped[str]
    tests: Mapped[str]
    tests_passed: Mapped[bool]
    version: Mapped[int] = mapped_column(default=1)
    uses: Mapped[int] = mapped_column(default=0)

    __table_args__ = (UniqueConstraint("agent_id", "name", "version", name="uq_skills_agent_name_version"),)


class SandboxRun(Base):
    __tablename__ = "sandbox_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    world_id: Mapped[str | None] = mapped_column(nullable=True)
    agent_id: Mapped[str | None] = mapped_column(nullable=True)
    tick: Mapped[int | None] = mapped_column(nullable=True)
    purpose: Mapped[str]
    image: Mapped[str]
    cmd_json: Mapped[str]
    exit_code: Mapped[int | None] = mapped_column(nullable=True)
    stdout: Mapped[str | None] = mapped_column(nullable=True)
    stderr: Mapped[str | None] = mapped_column(nullable=True)
    cpu_ms: Mapped[int | None] = mapped_column(nullable=True)
    mem_mb: Mapped[int | None] = mapped_column(nullable=True)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str]


class WebFetch(Base):
    __tablename__ = "web_fetches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    world_id: Mapped[str | None] = mapped_column(nullable=True)
    agent_id: Mapped[str | None] = mapped_column(nullable=True)
    tick: Mapped[int | None] = mapped_column(nullable=True)
    url: Mapped[str]
    domain: Mapped[str]
    allowed: Mapped[bool]
    http_status: Mapped[int | None] = mapped_column(nullable=True)
    bytes: Mapped[int | None] = mapped_column(nullable=True)
    sanitized_text: Mapped[str | None] = mapped_column(nullable=True)
    injection_flags: Mapped[str | None] = mapped_column(nullable=True)


class Autopsy(Base):
    __tablename__ = "autopsies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    tick: Mapped[int]
    cause: Mapped[str]
    summary_md: Mapped[str]
    lessons_json: Mapped[str]
    starter_playbook_md: Mapped[str | None] = mapped_column(nullable=True)
    successor_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    llm_call_id: Mapped[int | None] = mapped_column(nullable=True)


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    role: Mapped[str]
    version: Mapped[int]
    tasks_json: Mapped[str]
    pass_threshold: Mapped[float]
    held_out: Mapped[bool] = mapped_column(Boolean, default=True)


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    tick: Mapped[int]
    score: Mapped[float]
    passed: Mapped[bool]
    details_json: Mapped[str]


class Graduate(Base):
    __tablename__ = "graduates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    exam_attempt_id: Mapped[str] = mapped_column(ForeignKey("exam_attempts.id"))
    package_path: Mapped[str]
    package_sha256: Mapped[str]
    status: Mapped[str] = mapped_column(default="pending_review")
    reviewed_by: Mapped[str | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(nullable=True)
    review_notes: Mapped[str | None] = mapped_column(nullable=True)
    exported_at: Mapped[str | None] = mapped_column(nullable=True)


class MarketItem(Base):
    __tablename__ = "market_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    world_id: Mapped[str | None] = mapped_column(nullable=True)
    name: Mapped[str | None] = mapped_column(nullable=True)
    price: Mapped[int | None] = mapped_column(nullable=True)
    effect_json: Mapped[str | None] = mapped_column(nullable=True)


class ProviderHealth(Base):
    __tablename__ = "provider_health"

    provider: Mapped[str] = mapped_column(String, primary_key=True)
    rpm_limit: Mapped[int | None] = mapped_column(nullable=True)
    tpm_limit: Mapped[int | None] = mapped_column(nullable=True)
    cooldown_until: Mapped[str | None] = mapped_column(nullable=True)
    consecutive_errors: Mapped[int] = mapped_column(default=0)
    error_rate: Mapped[float] = mapped_column(default=0.0)
    retired: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[str | None] = mapped_column(nullable=True)


class Snapshot(Base):
    __tablename__ = "snapshots"

    world_id: Mapped[str] = mapped_column(String, primary_key=True)
    tick: Mapped[int] = mapped_column(primary_key=True)
    state_json: Mapped[str]
    event_hash: Mapped[str]


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(nullable=True)
    preset: Mapped[str | None] = mapped_column(nullable=True)
    seeds_json: Mapped[str | None] = mapped_column(nullable=True)
    world_ids_json: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str | None] = mapped_column(nullable=True)
    report_path: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[str | None] = mapped_column(nullable=True)
