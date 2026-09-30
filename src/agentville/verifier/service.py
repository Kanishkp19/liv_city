"""VerifierService: fixed stage pipeline, fail closed (TRD S6, VERIFIERS S1)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


class VerifierError(Exception):
    """Any verifier failure -> job fails (never a default pass)."""


@dataclass
class StageResult:
    stage: str
    passed: bool
    score: float | None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class VerificationResult:
    passed: bool
    quality: float
    stages: list[StageResult] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    error: str | None = None


# --- content_post_v1 structural schema (VERIFIERS S2) -------------------------

SCHEMA_CONTENT_POST_V1 = {
    "type": "object",
    "required": ["hook", "script", "captions", "tags"],
    "properties": {
        "hook": {"type": "string", "maxLength": 120},
        "script": {"type": "string", "minLength": 80, "maxLength": 1200},
        "captions": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 12},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 10},
    },
}


class VerifierService:
    """Pipeline: structural -> programmatic (-> judge later phases). Fail closed."""

    def __init__(self) -> None:
        self._global_corpus: list[set[str]] = []

    def verify(self, job: Any, artifact: dict[str, Any]) -> VerificationResult:
        """Run the recipe stages; any exception => failed result with verifier_error flag."""
        stages: list[StageResult] = []
        try:
            recipe = job.verifier_recipe
            if recipe.stages:
                for stage_cfg in recipe.stages:
                    r = self._run_stage(job, artifact, stage_cfg)
                    stages.append(r)
                    if not r.passed:
                        return VerificationResult(passed=False, quality=0.0, stages=stages, flags=["stage_fail"])
            else:
                # no recipe: fail closed
                return VerificationResult(passed=False, quality=0.0, stages=[], flags=["no_recipe"])
        except Exception as e:  # noqa: BLE001
            return VerificationResult(
                passed=False, quality=0.0, stages=stages,
                flags=["verifier_error"], error=str(e),
            )
        prog = next((s for s in stages if s.stage == "programmatic"), None)
        score = float(prog.score) if prog and prog.score is not None else 0.0
        return VerificationResult(passed=True, quality=score, stages=stages)

    def _run_stage(self, job: Any, artifact: dict[str, Any], cfg: dict[str, Any]) -> StageResult:
        if cfg.get("type") == "structural":
            return self._structural(artifact)
        if cfg.get("type") == "programmatic":
            return self._programmatic_content(job, artifact)
        return StageResult(stage=str(cfg.get("type", "?")), passed=False, score=None, error="unknown stage")

    # -- stages ------------------------------------------------------------
    def _structural(self, artifact: dict[str, Any]) -> StageResult:
        import jsonschema

        try:
            jsonschema.validate(artifact, SCHEMA_CONTENT_POST_V1)
            return StageResult(stage="structural", passed=True, score=1.0)
        except jsonschema.ValidationError as e:
            return StageResult(stage="structural", passed=False, score=0.0, details={"error": e.message})

    def _programmatic_content(self, job: Any, artifact: dict[str, Any]) -> StageResult:
        """Checks from VERIFIERS S3; config keys arrive via job.params (hidden)."""
        cfg = job.params or {}
        checks: dict[str, Any] = {}
        gates = True

        hook_words = len(str(artifact.get("hook", "")).split())
        checks["hook_length"] = {"ok": hook_words <= 12, "hook_words": hook_words}
        gates &= hook_words <= 12

        banned = list(cfg.get("banned_words", []))
        flat = json.dumps(artifact, ensure_ascii=False).lower()
        bad = [w for w in banned if str(w).lower() in flat]
        checks["banned_words"] = {"ok": not bad, "hits": bad}
        gates &= not bad

        missing = [t for t in cfg.get("must_include", []) if str(t).lower() not in flat]
        req_total = len(cfg.get("must_include", [])) or 1
        req_score = 1.0 - (len(missing) / req_total)
        checks["required_terms"] = {"missing": missing, "score": req_score}

        cta = str(cfg.get("cta", ""))
        difficulty = int(getattr(job, "difficulty", 1) or 1)
        cta_gated = difficulty >= 2  # VERIFIERS S3: gate only for difficulty>=2
        checks["cta_present"] = {"ok": (not cta) or (cta.lower() in flat), "gated": cta_gated}
        if cta and cta_gated:
            gates &= bool(cta.lower() in flat)

        script = str(artifact.get("script", ""))
        words = len(script.split())
        est_s = words / 2.5
        lo, hi = (cfg.get("duration_band") or (int(cfg.get("duration_s", 30)) * 0.7, int(cfg.get("duration_s", 30)) * 1.3))
        dur_ok = lo <= est_s <= hi
        checks["duration_est"] = {"est_s": est_s, "ok": dur_ok, "target_s": cfg.get("duration_s")}
        gates &= True  # duration is scored, not gated (linear penalty spirit)

        tags = list(artifact.get("tags", []))
        tags_ok = all(t == t.lower() and " " not in t for t in tags) and len(set(tags)) == len(tags)
        checks["tag_quality"] = {"ok": tags_ok}
        if not tags_ok:
            gates = False

        dupe = self._dupe_check(script)
        checks["dupe_check"] = {"similarity": dupe, "ok": dupe < 0.5}
        gates &= dupe < 0.5

        fractions = [checks["required_terms"]["score"]]
        if gates:
            return StageResult(stage="programmatic", passed=True, score=sum(fractions) / len(fractions), details=checks)
        return StageResult(stage="programmatic", passed=False, score=0.0, details=checks)

    def _dupe_check(self, script: str) -> float:
        """Jaccard 3-gram similarity vs the best of the last 20 artifacts."""
        grams = _ngrams(script)
        best = 0.0
        for prev in self._global_corpus[-20:]:
            if prev and grams:
                inter = len(grams & prev)
                union = len(grams | prev)
                if union:
                    best = max(best, inter / union)
        self._global_corpus.append(grams)
        return best


def _ngrams(text: str, n: int = 3) -> set[str]:
    ws = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(ws[i : i + n]) for i in range(len(ws) - n + 1)} if len(ws) >= n else {text.lower()}


# --- settlement --------------------------------------------------------------

def settle_payment(
    world: Any,
    ledger: Any,
    events: Any,
    job: Any,
    result: VerificationResult,
    late: bool,
    late_multiplier: float,
    rep_deltas: dict[str, float],
    session: Any = None,
) -> int:
    """Record verification stage rows, then pay verified work; mirrors docs' trigger invariant."""
    from agentville.engine.payout import compute_payout, reputation_delta

    agent = world.agents[job.assigned_agent]
    quality = result.quality if result.passed else 0.0
    payout = compute_payout(
        base_reward=job.reward, quality=quality, quality_tiers=world.economy.quality_tiers,
        late=late, late_multiplier=late_multiplier,
    )
    # persist the programmatic verification row the payment trigger requires (I5)
    # raw ordered SQL: avoids ORM unit-of-work reordering across agent/event inserts
    if session is not None:
        from sqlalchemy import text as sql_text

        art_id = f"art_{job.id}_{world.tick}"
        session.execute(
            sql_text(
                "INSERT OR IGNORE INTO artifacts (id, world_id, agent_id, job_id, tick, kind, path, sha256, size_bytes, meta_json) "
                "VALUES (:i, :w, :a, :j, :t, 'json', :p, :s, 0, '{}')"
            ),
            {"i": art_id, "w": world.id, "a": agent.id, "j": job.id, "t": world.tick, "p": f"{world.id}/{art_id}.json", "s": "0" * 64},
        )
        for stage in result.stages:
            session.execute(
                sql_text(
                    "INSERT OR IGNORE INTO verifications (id, world_id, job_id, artifact_id, stage, passed, score, details_json, tick, error) "
                    "VALUES (:i, :w, :j, :a, :st, :p, :sc, :d, :t, :e)"
                ),
                {"i": f"ver_{job.id}_{stage.stage}_{world.tick}", "w": world.id, "j": job.id,
                 "a": art_id, "st": stage.stage, "p": int(stage.passed), "sc": stage.score,
                 "d": json.dumps(stage.details or {}), "t": world.tick, "e": stage.error},
            )
        session.flush()
    if payout > 0:
        from agentville.engine.market import apply_payment

        evt = events.emit(
            world.id, tick=world.tick, type_="verification_done", agent_id=agent.id,
            payload={"job_id": job.id, "passed": True, "quality": quality},
        )
        apply_payment(world, ledger, job_id=job.id, buyer_id=job.buyer_id, agent_id=agent.id,
                      payout=payout, event_id=evt)
    else:
        events.emit(
            world.id, tick=world.tick, type_="verification_done", agent_id=agent.id,
            payload={"job_id": job.id, "passed": result.passed, "quality": quality},
        )
    agent.vitals.reputation = max(
        0.0, min(100.0, agent.vitals.reputation + reputation_delta(quality, rep_deltas))
    )
    return payout
