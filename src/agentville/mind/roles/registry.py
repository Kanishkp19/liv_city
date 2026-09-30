"""Role registry: job templates + verifier recipes for the code-verifiable roles (T8.1-T8.3)."""

from __future__ import annotations

import json
import random

from agentville.engine.types import JobSpec, VerifierRecipe

FUNCTION_POOL = [
    ("add", ["a", "b"], "a + b"),
    ("mul", ["a", "b"], "a * b"),
    ("max_of", ["a", "b"], "a if a > b else b"),
    ("clamp01", ["x"], "max(0, min(1, x))"),
    ("neg", ["x"], "-x"),
    ("square", ["x"], "x * x"),
]


class RoleTemplates:
    """Template registry per role; deterministic given rng (TRD S3.3)."""

    @staticmethod
    def make(role: str, rng: random.Random, difficulty: int, job_id: str, buyer_id: str, tick: int,
             deadline_ticks: dict[int, int], reward: int) -> JobSpec:
        if role == "developer":
            return RoleTemplates._developer(rng, difficulty, job_id, buyer_id, tick, deadline_ticks, reward)
        if role == "data_analyst":
            return RoleTemplates._analyst(rng, difficulty, job_id, buyer_id, tick, deadline_ticks, reward)
        if role == "ops_clerk":
            return RoleTemplates._clerk(rng, difficulty, job_id, buyer_id, tick, deadline_ticks, reward)
        # content_creator (default; engine/jobs.py has the richer template)
        from agentville.engine.jobs import JobTemplate

        return JobTemplate.make(rng, difficulty, job_id, buyer_id, tick, deadline_ticks, reward)

    @staticmethod
    def _developer(rng: random.Random, difficulty: int, job_id: str, buyer_id: str, tick: int,
                   deadline_ticks: dict[int, int], reward: int) -> JobSpec:
        name, arg_list, _expr = rng.choice(FUNCTION_POOL)
        n_tests = {1: 3, 2: 5, 3: 8}[difficulty]
        cases = [(round(rng.uniform(-10, 10), 2), round(rng.uniform(-10, 10), 2)) for _ in range(n_tests)]
        visible = {"function": name, "signature": f"def {name}({', '.join(arg_list)}):", "n_hidden_tests": n_tests}
        hidden = {**visible, "cases": cases[:2], "extra_cases": cases[2:], "role_kind": "developer"}
        recipe = VerifierRecipe.model_validate({
            "stages": [
                {"type": "structural", "schema": "python_module_v1"},
                {"type": "programmatic", "checks": ["hidden_pytest", "ast_import_bans"], "config": {"name": name, "args": arg_list}},
            ],
            "quality_weights": {"programmatic": 1.0},
        })
        brief = f"Write a Python module defining {name}{tuple(arg_list)} exactly to spec. Hidden pytest will verify it."
        return JobSpec(
            id=job_id, role="developer", title=f"Implement {name}() (d{difficulty})", buyer_id=buyer_id,
            brief=brief,
            params=hidden, visible_params=visible, reward=reward, difficulty=difficulty,  # type: ignore[arg-type]
            posted_tick=tick, deadline_tick=tick + deadline_ticks[difficulty], verifier_recipe=recipe,
        )

    @staticmethod
    def _analyst(rng: random.Random, difficulty: int, job_id: str, buyer_id: str, tick: int,
                 deadline_ticks: dict[int, int], reward: int) -> JobSpec:
        base = rng.randint(100, 900)
        rate = round(rng.uniform(0.05, 0.3), 3)
        n = {1: 6, 2: 12, 3: 24}[difficulty]
        answer = round(base * (1 + rate) ** n, 2)
        question = f"A value starts at {base} and grows {rate} per step for {n} steps. Final value?"
        visible = {"question": question, "tolerance": 0.05}
        hidden = {**visible, "answer": answer, "role_kind": "data_analyst"}
        recipe = VerifierRecipe.model_validate({
            "stages": [{"type": "programmatic", "checks": ["numeric_answer", "method_present"], "config": hidden}],
            "quality_weights": {"programmatic": 1.0},
        })
        return JobSpec(
            id=job_id, role="data_analyst", title=f"Compute compound growth (d{difficulty})", buyer_id=buyer_id,
            brief=question, params=hidden, visible_params=visible,
            reward=reward, difficulty=difficulty,  # type: ignore[arg-type]
            posted_tick=tick, deadline_tick=tick + deadline_ticks[difficulty], verifier_recipe=recipe,
        )

    @staticmethod
    def _clerk(rng: random.Random, difficulty: int, job_id: str, buyer_id: str, tick: int,
               deadline_ticks: dict[int, int], reward: int) -> JobSpec:
        rows = [{"id": i, "qty": rng.randint(1, 9), "unit": rng.randint(2, 20)} for i in range({1: 5, 2: 8, 3: 12}[difficulty])]
        task_text = "Given rows (id,qty,unit), output JSON list of {id,total}."
        rows_json = json.dumps(rows)[:200]
        brief = f"{task_text} rows={rows_json}"
        expected = [{"id": r["id"], "total": r["qty"] * r["unit"]} for r in rows]
        visible = {"task": task_text, "rows": rows}
        hidden = {**visible, "expected": expected, "f1_threshold": 0.9, "role_kind": "ops_clerk"}
        recipe = VerifierRecipe.model_validate({
            "stages": [{"type": "programmatic", "checks": ["row_hash_f1"], "config": {"f1_threshold": 0.9}}],
            "quality_weights": {"programmatic": 1.0},
        })
        return JobSpec(
            id=job_id, role="ops_clerk", title=f"Totals table (d{difficulty})", buyer_id=buyer_id,
            brief=brief, params=hidden, visible_params=visible,
            reward=reward, difficulty=difficulty,  # type: ignore[arg-type]
            posted_tick=tick, deadline_tick=tick + deadline_ticks[difficulty], verifier_recipe=recipe,
        )
