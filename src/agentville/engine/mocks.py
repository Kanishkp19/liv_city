"""Mock agent minds: oracle / noop / random_valid / adversarial (PROMPTS S8, T1.7)."""

from __future__ import annotations

from typing import Any

from agentville.engine.jobs import JobBoard, JobStatus
from agentville.engine.types import AgentState, Proposal
from agentville.engine.world import World
from agentville.rng import derive_rng


def mock_artifact(seed_key: str, role: str, params: dict[str, Any]) -> dict[str, Any]:
    """Deterministic, verifier-passing content artifact for oracle agents."""
    topic = str(params.get("topic", "coffee"))
    tone = str(params.get("tone", "calm"))
    cta = str(params.get("cta", "follow for more"))
    must = params.get("must_include", [topic])
    duration = int(params.get("duration_s", 30))
    words = duration * 3  # 3 wps target -> inside duration band
    body = " ".join(f"{topic} {tone} tip {i}" for i in range(words))
    if len(body) > 1150:  # structural cap is 1200 (docs); mock targets 1150 for safety
        filler = f"quick {topic} {tone} guide"
        reps = (1150 - 60) // (len(filler) + 1)
        body = " ".join([f"{topic} {tone} tips:"] + [filler] * max(reps, 40))
        body = body[:1150].rsplit(" ", 1)[0]
    body += f" {cta}"  # brief demands the CTA
    for i, term in enumerate(must):
        if str(term) not in body:
            body += f" {term} {i}"
    return {
        "hook": f"why {topic} changes everything",
        "script": body,
        "captions": [f"{topic} tip one", f"{topic} tip two", f"{topic} tip three"],
        "tags": [topic.replace(" ", ""), tone, "shorts"],
    }


class MockMind:
    """Scripted decide() for P1: no LLM needed."""

    def __init__(self, policy: str) -> None:
        self.policy = policy

    def decide(self, world: World, agent: AgentState) -> Proposal:
        rng = derive_rng(world.seed, world.tick, "decide", agent.id)
        open_jobs = JobBoard(world).open_jobs_for(agent.role, agent.vitals.reputation)

        if self.policy == "noop":
            return Proposal(action="noop", reason="noop policy")

        if self.policy == "adversarial":
            pick = rng.random()
            if pick < 0.4:
                return Proposal(action="set_balance", args={"funds": 999_999}, reason="tamper")
            if pick < 0.7:
                return Proposal(action="take_job", args={"job_id": "job_missing"}, reason="probe")
            return Proposal(action="work_on", args={"job_id": "nope", "effort": 9}, reason="probe")

        if self.policy == "random_valid":
            r = rng.random()
            if agent.vitals.energy < 20:
                return Proposal(action="rest", reason="tired")
            if r < 0.4 and open_jobs and agent.current_job_id is None:
                return Proposal(action="take_job", args={"job_id": open_jobs[0].id}, reason="random take")
            if agent.current_job_id and r < 0.8:
                return Proposal(action="work_on", args={"job_id": agent.current_job_id, "effort": rng.randint(1, 3)}, reason="random work")
            return Proposal(action="noop", reason="random")

        # oracle: eat -> take -> work -> submit loop; rest when tired
        if agent.vitals.energy < 25:
            return Proposal(action="rest", reason="restore energy")
        job = None
        if agent.current_job_id:
            job = world.jobs.get(agent.current_job_id)
        if job is None and open_jobs:
            return Proposal(action="take_job", args={"job_id": open_jobs[0].id}, reason="earn")
        if job is not None and job.status == JobStatus.TAKEN:
            return Proposal(action="submit_work", args={"job_id": job.id, "artifact_id": f"art_{job.id}_{world.tick}"}, reason="ship it")
        if job is not None and job.status == JobStatus.TAKEN and agent.vitals.energy >= 5:
            return Proposal(action="work_on", args={"job_id": job.id, "effort": 2}, reason="work")
        return Proposal(action="eat", reason="stay fed")
