"""Job generation and the job board state machine (TRD S3.3/S3.4, T1.3/T1.4)."""

from __future__ import annotations

import json
from typing import Any

from agentville.engine.types import JobSpec, JobStatus, VerifierRecipe

__all__ = ["JobBoard", "JobError", "JobGenerator", "JobTemplate", "JobStatus", "dumps_visible"]
from agentville.engine.world import World
from agentville.rng import derive_rng


class JobError(Exception):
    """Illegal job board transition or bad job state."""


# ---------------------------------------------------------------------------
# Templates (content_creator first; registry pattern per AGENT_ROLES S1)
# ---------------------------------------------------------------------------

TOPICS = [
    "morning routines", "street food", "productivity apps", "budget travel", "home workouts",
    "coffee brewing", "study hacks", "pet care", "sustainable living", "mini drones",
]
TONES = ["energetic", "calm", "witty", "documentary", "cozy"]
CTAS = ["follow for more", "comment your take", "save this", "share with a friend", "link in bio"]


class JobTemplate:
    """Builds a deterministic JobSpec for a role/difficulty."""

    role = "content_creator"

    @staticmethod
    def make(rng: Any, difficulty: int, job_id: str, buyer_id: str, tick: int, deadline_ticks: dict[int, int], reward: int) -> JobSpec:
        """Deterministic job from an injected derive_rng() stream (never random module directly)."""
        topic = rng.choice(TOPICS)
        tone = rng.choice(TONES)
        cta = rng.choice(CTAS)
        banned = rng.sample(["crypto", "guaranteed", "shocking", "cure", "miracle", "hack x"], k=3)
        must_include = [f"{topic}", tone]
        duration = {1: (15, 30), 2: (25, 45), 3: (40, 60)}[difficulty]
        visible: dict[str, Any] = {
            "topic": topic, "tone": tone, "cta": cta,
            "banned_words": banned, "must_include": must_include,
            "duration_s": rng.randint(*duration),
        }
        hidden: dict[str, Any] = {
            **visible,
            "max_hook_words": 12,
            "dupe_threshold_personal": 0.5,
            "dupe_threshold_global": 0.6,
            "readability_band": [60, 90],
            "seed": rng.randint(0, 2**31),
        }
        recipe = VerifierRecipe.model_validate({
            "stages": [
                {"type": "structural", "schema": "content_post_v1"},
                {"type": "programmatic", "checks": ["hook_length", "banned_words", "required_terms", "cta_present", "duration_est", "readability", "dupe_check", "tag_quality"], "config": hidden},
            ],
            "quality_weights": {"programmatic": 1.0},
        })
        return JobSpec(
            id=job_id, role=JobTemplate.role,
            title=f"{tone.title()} {topic} short (d{difficulty})",
            buyer_id=buyer_id,
            brief=f"Make a {visible['duration_s']}s {tone} short-form video script about {topic}. "
                  f"End with CTA: {cta}. Never use: {', '.join(banned)}.",
            params=hidden, visible_params=visible,
            reward=reward, difficulty=difficulty,  # type: ignore[arg-type]
            posted_tick=tick, deadline_tick=tick + deadline_ticks[difficulty],
            verifier_recipe=recipe,
        )


# ---------------------------------------------------------------------------
# JobGenerator (TRD S3.3)
# ---------------------------------------------------------------------------

class JobGenerator:
    """Generates jobs per tick: Poisson counts, 50/35/15 difficulty, ~5% audit plants."""

    def __init__(self, world: World) -> None:
        self.world = world

    def generate(self, tick: int) -> list[JobSpec]:
        """Jobs posted at tick; deterministic under world seed."""
        eco = self.world.economy
        if eco is None:
            msg = "world.economy required"
            raise ValueError(msg)
        # TRD S3.3: rng keyed by the tick being generated, not world.tick
        rng = derive_rng(self.world.seed, tick, "jobs")
        out: list[JobSpec] = []
        for role in self._roles():
            alive = len([a for a in self.world.agents_by_role(role)]) or 1
            lam = eco.job_rate * alive
            count = _poisson(rng, lam)
            open_in_role = sum(
                1 for j in self.world.jobs.values()
                if j.role == role and j.status in (JobStatus.OPEN, JobStatus.TAKEN, JobStatus.SUBMITTED)
            )
            count = min(count, max(0, eco.max_open_per_role - open_in_role))
            for _ in range(count):
                difficulty = rng.choices([1, 2, 3], weights=[50, 35, 15], k=1)[0]
                is_plant = rng.random() < eco.audit_rate
                buyer_id = self._pick_buyer(rng)
                job = JobTemplate.make(
                    rng, difficulty, job_id=self.world.ids.next("job"), buyer_id=buyer_id,
                    tick=tick, deadline_ticks=eco.deadline_ticks, reward=eco.job_rewards[difficulty],
                )
                job.is_audit_plant = is_plant
                out.append(job)
        return out

    def _roles(self) -> list[str]:
        return sorted({a.role for a in self.world.alive_agents()}) or ["content_creator"]

    def _pick_buyer(self, rng: Any) -> str:
        buyers = [a.split(":", 1)[1] for a in self.world.accounts if a.startswith("buyer:")]
        return rng.choice(sorted(buyers)) if buyers else "b1"


def _poisson(rng: Any, lam: float) -> int:
    """Knuth's method; deterministic given rng."""
    L = pow(2.718281828459045, -lam)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


# ---------------------------------------------------------------------------
# JobBoard state machine (TRD S3.4)
# ---------------------------------------------------------------------------

_LEGAL: dict[JobStatus, set[JobStatus]] = {
    JobStatus.OPEN: {JobStatus.TAKEN, JobStatus.EXPIRED},
    JobStatus.TAKEN: {JobStatus.SUBMITTED, JobStatus.EXPIRED, JobStatus.OPEN},
    JobStatus.SUBMITTED: {JobStatus.VERIFIED_PASS, JobStatus.VERIFIED_FAIL},
    JobStatus.VERIFIED_PASS: set(),
    JobStatus.VERIFIED_FAIL: set(),
    JobStatus.EXPIRED: set(),
}


class JobBoard:
    """Enforces the job status state machine."""

    def __init__(self, world: World) -> None:
        self.world = world

    def transition(self, job_id: str, to: JobStatus) -> JobSpec:
        """Apply a legal transition or raise JobError."""
        job = self.world.jobs.get(job_id)
        if job is None:
            msg = f"unknown job {job_id}"
            raise JobError(msg)
        if to not in _LEGAL[job.status]:
            msg = f"illegal transition {job.status} -> {to} for {job_id}"
            raise JobError(msg)
        job.status = to
        return job

    def expire_past_deadline(self, tick: int, grace: int, late_mult: float) -> list[JobSpec]:
        """Expire OPEN/TAKEN jobs past deadline+grace; applies penalties downstream."""
        expired: list[JobSpec] = []
        for job in self.world.jobs.values():
            if job.status in (JobStatus.OPEN, JobStatus.TAKEN) and tick > job.deadline_tick + grace:
                self.transition(job.id, JobStatus.EXPIRED)
                expired.append(job)
        return expired

    def open_jobs_for(self, role: str, reputation: float, limit: int = 8) -> list[JobSpec]:
        """Visible OPEN jobs matching role and reputation floor, best first."""
        jobs = [
            j for j in self.world.jobs.values()
            if j.status == JobStatus.OPEN and j.role == role and reputation >= j.min_reputation
        ]
        jobs.sort(key=lambda j: (-j.reward, j.deadline_tick, j.id))
        return jobs[:limit]


def dumps_visible(job: JobSpec) -> str:
    """JSON of the agent-visible slice of a job (never hidden params)."""
    return json.dumps({"id": job.id, "title": job.title, "reward": job.reward, "difficulty": job.difficulty,
                       "deadline_tick": job.deadline_tick, "brief": job.brief, "params": job.visible_params})
