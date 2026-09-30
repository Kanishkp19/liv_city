"""Core domain types (TRD S2). Money is integer coins; never float."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

Coins = int


class AgentStatus(StrEnum):
    ALIVE = "alive"
    DEAD = "dead"
    GRADUATED = "graduated"
    PIVOTED = "pivoted"


class JobStatus(StrEnum):
    OPEN = "open"
    TAKEN = "taken"
    SUBMITTED = "submitted"
    VERIFIED_PASS = "verified_pass"
    VERIFIED_FAIL = "verified_fail"
    EXPIRED = "expired"


class GroupType(StrEnum):
    LEARNER = "learner"
    CONTROL_A = "control_a"
    CONTROL_B = "control_b"
    CONTROL_C = "control_c"


class Vitals(BaseModel):
    """Agent vitals; funds are Coins (int), reputation bounded 0..100."""

    energy: int = Field(ge=0, le=100)
    funds: Coins
    reputation: float = Field(ge=0, le=100)
    strikes: int = 0


class AgentState(BaseModel):
    """In-memory agent aggregate synced to DB rows each tick."""

    id: str
    world_id: str
    role: str
    generation: int = 1
    parent_id: str | None = None
    group_type: GroupType
    status: AgentStatus = AgentStatus.ALIVE
    vitals: Vitals
    location: str = "housing"
    born_tick: int = 0
    current_job_id: str | None = None
    inventory: dict[str, int] = Field(default_factory=dict)
    idle_ticks: int = 0
    low_energy_ticks: int = 0
    negative_funds_ticks: int = 0


class VerifierRecipe(BaseModel):
    """Verifier pipeline definition stored per job (BACKEND_SCHEMA S4 shape)."""

    stages: list[dict[str, Any]]
    quality_weights: dict[str, float] = Field(default_factory=dict)


class JobSpec(BaseModel):
    """A posted job. params may include hidden fields agents never see."""

    id: str
    role: str
    title: str
    buyer_id: str
    brief: str
    params: dict[str, Any] = Field(default_factory=dict)
    visible_params: dict[str, Any] = Field(default_factory=dict)
    reward: Coins
    penalty: Coins = 0
    difficulty: Literal[1, 2, 3]
    min_reputation: float = 0.0
    posted_tick: int
    deadline_tick: int
    verifier_recipe: VerifierRecipe = VerifierRecipe(stages=[], quality_weights={})
    is_audit_plant: bool = False
    status: JobStatus = JobStatus.OPEN
    assigned_agent: str | None = None


class Proposal(BaseModel):
    """What the LLM returns: exactly one action with args and a reason."""

    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="", max_length=400)


class ActionResult(BaseModel):
    """Gateway verdict for one proposal."""

    status: Literal["accepted", "rejected", "error"]
    reject_reason: str | None = None
    energy_cost: int = 0
    coin_delta: Coins = 0
    observation: str
