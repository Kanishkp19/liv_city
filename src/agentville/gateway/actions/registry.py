"""Action registry: all 14 v1 actions (TRD S3.7)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agentville.gateway.actions.base import ActionSpec


class TakeJobArgs(BaseModel):
    job_id: str


class WorkOnArgs(BaseModel):
    job_id: str
    effort: int = Field(ge=1, le=3)
    approach: str = Field(default="", max_length=300)


class SubmitWorkArgs(BaseModel):
    job_id: str
    artifact_id: str


class WriteNoteArgs(BaseModel):
    text: str = Field(max_length=280)
    importance: int = Field(ge=1, le=5)


class UpdatePlaybookArgs(BaseModel):
    body_md: str = Field(max_length=2000)
    evidence_job_ids: list[str] = Field(default_factory=list)


class SaveSkillArgs(BaseModel):
    name: str = Field(max_length=64)
    code: str
    tests: str


class RunSkillArgs(BaseModel):
    name: str
    input: str = Field(default="")


class StudyWebArgs(BaseModel):
    url: str | None = None
    query: str | None = None


class BuyItemArgs(BaseModel):
    item_id: str


class EmptyArgs(BaseModel):
    pass


class RequestExamArgs(BaseModel):
    exam_id: str


class QuitJobArgs(BaseModel):
    job_id: str


def build_registry() -> dict[str, ActionSpec]:
    """The 14 actions with their energy/coin costs from TRD S3.7."""
    specs: list[ActionSpec] = [
        ActionSpec(name="take_job", arg_schema=TakeJobArgs, energy_cost=2, description="Assign an OPEN job"),
        ActionSpec(name="work_on", arg_schema=WorkOnArgs, energy_per_effort=5, description="Add progress to active job"),
        ActionSpec(name="submit_work", arg_schema=SubmitWorkArgs, energy_cost=1, description="Move job to SUBMITTED"),
        ActionSpec(name="write_note", arg_schema=WriteNoteArgs, energy_cost=0, description="Notebook entry"),
        ActionSpec(name="update_playbook", arg_schema=UpdatePlaybookArgs, energy_cost=1, description="New playbook version"),
        ActionSpec(name="save_skill", arg_schema=SaveSkillArgs, energy_cost=3, description="Save skill if tests pass"),
        ActionSpec(name="run_skill", arg_schema=RunSkillArgs, energy_cost=2, description="Run saved skill"),
        ActionSpec(name="study_web", arg_schema=StudyWebArgs, energy_cost=1, coin_cost=5, description="Read-only study fetch"),
        ActionSpec(name="buy_item", arg_schema=BuyItemArgs, energy_cost=0, description="Buy market item"),
        ActionSpec(name="rest", arg_schema=EmptyArgs, energy_cost=-30, description="Restore energy"),
        ActionSpec(name="eat", arg_schema=EmptyArgs, energy_cost=0, description="Pay food cost"),
        ActionSpec(name="request_exam", arg_schema=RequestExamArgs, energy_cost=10, description="Start graduation exam"),
        ActionSpec(name="quit_job", arg_schema=QuitJobArgs, energy_cost=0, description="Release job, -5 reputation"),
        ActionSpec(name="noop", arg_schema=EmptyArgs, energy_cost=0, description="Explicit skip"),
    ]
    return {s.name: s for s in specs}


def get_spec(name: str) -> ActionSpec | None:
    """Lookup or None for unknown actions."""
    return build_registry().get(name)


def spec_args_model(name: str) -> type[BaseModel] | None:
    """Arg schema class for an action name."""
    spec: dict[str, ActionSpec] | None
    spec = REGISTRY_CACHE.get("registry")
    if spec is None:
        REGISTRY_CACHE["registry"] = spec = build_registry()
    s = spec.get(name)
    return s.arg_schema if s else None


REGISTRY_CACHE: dict[str, Any] = {}
