"""Phase 8: role templates + code verifiers + gold fixtures + calibration sanity."""

from __future__ import annotations

import random

from agentville.engine.types import JobStatus
from agentville.mind.roles.registry import RoleTemplates
from agentville.verifier.recipes_code import (
    ast_import_bans,
    hidden_pytest_grade,
    numeric_answer_check,
    row_hash_f1,
)


def _deadline() -> dict[int, int]:
    return {1: 4, 2: 6, 3: 10}


def test_developer_template_deterministic() -> None:
    j1 = RoleTemplates.make("developer", random.Random(3), 2, "job_1", "b", 1, _deadline(), 90)
    j2 = RoleTemplates.make("developer", random.Random(3), 2, "job_1", "b", 1, _deadline(), 90)
    assert j1.brief == j2.brief and j1.params["function"] == j2.params["function"]


def test_all_roles_generate() -> None:
    for role in ("content_creator", "developer", "data_analyst", "ops_clerk"):
        j = RoleTemplates.make(role, random.Random(1), 1, f"job_{role}", "b", 1, _deadline(), 40)
        assert j.role == role and j.status == JobStatus.OPEN


def test_ast_import_bans() -> None:
    assert ast_import_bans("import os\nx = 1") == ["os"]
    assert ast_import_bans("from subprocess import run") == ["subprocess"]
    assert ast_import_bans("import math\ny = math.pi") == []
    assert "syntax_error" in ast_import_bans("def broken(:  # noqa")


def test_hidden_pytest_grader() -> None:
    good = "def add(a, b):\n    return a + b\n"
    bad = "def add(a, b):\n    return a - b\n"
    evil = "import os\ndef add(a, b):\n    os.system('x')\n    return a + b\n"
    cases = [{"a": 1, "b": 2, "expected": 3}, {"a": 0, "b": 5, "expected": 5}]
    r_good = hidden_pytest_grade(good, cases, "add", ["a", "b"])
    r_bad = hidden_pytest_grade(bad, cases, "add", ["a", "b"])
    r_evil = hidden_pytest_grade(evil, cases, "add", ["a", "b"])
    assert r_good["passed"] and r_good["score"] == 1.0
    assert not r_bad["passed"] and r_bad["score"] == 0.0
    assert not r_evil["passed"] and "os" in r_evil["details"]["banned_imports"]


def test_numeric_answer_check() -> None:
    r = numeric_answer_check({"answer": 103.0, "method": "compound"}, expected=100.0, tol=0.05)
    assert r["passed"]
    r2 = numeric_answer_check({"answer": 150.0, "method": "guess"}, expected=100.0, tol=0.05)
    assert not r2["passed"]
    r3 = numeric_answer_check({"answer": 100.0}, expected=100.0, tol=0.05)
    assert not r3["passed"]  # method missing


def test_row_hash_f1() -> None:
    expected = [{"id": 1, "total": 10}, {"id": 2, "total": 20}, {"id": 3, "total": 30}]
    perfect = {"rows": expected}
    partial = {"rows": expected[:2]}
    assert row_hash_f1(perfect, expected, 0.9)["passed"]
    assert not row_hash_f1(partial, expected, 0.9)["passed"]
    assert abs(row_hash_f1(partial, expected, 0.9)["score"] - 0.8) < 1e-9


def test_gold_set_classification_content() -> None:
    """Gold sanity: obviously-good mock artifacts pass, corrupted ones fail (>=95% target)."""
    from agentville.engine.mocks import mock_artifact
    from agentville.mind.roles.registry import RoleTemplates
    from agentville.verifier.service import VerifierService

    v = VerifierService()
    ok = bad = 0
    for i in range(20):
        job = RoleTemplates.make("content_creator", random.Random(i), 1, f"job_{i}", "b", 1, _deadline(), 40)
        good_art = mock_artifact("g", job.role, job.params)
        ok += int(v.verify(job, good_art).passed)
        bad_art = dict(good_art)
        bad_art["hook"] = "x" * 200  # violates structural cap
        bad_art["tags"] = ["UPPER TAG"]  # violates tag quality
        bad += int(not v.verify(job, bad_art).passed)
    assert ok >= 18 and bad >= 19  # >=90%/95% over 20 trials; dupe corpus may penalize near-duplicates
