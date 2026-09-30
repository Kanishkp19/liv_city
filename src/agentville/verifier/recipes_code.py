"""Programmatic verifiers for code/data roles (VERIFIERS S4-S5)."""

from __future__ import annotations

import ast
import json
from typing import Any

BANNED_IMPORTS = {"os", "subprocess", "socket", "requests", "shutil", "sys"}


def ast_import_bans(code: str) -> list[str]:
    """AST scan for banned imports (defense in depth; sandbox is the real barrier)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ["syntax_error"]
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            hits.extend(a.name.split(".")[0] for a in node.names if a.name.split(".")[0] in BANNED_IMPORTS)
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in BANNED_IMPORTS:
            hits.append(node.module.split(".")[0])
    return hits


def hidden_pytest_grade(code: str, cases: list[dict[str, Any]], fn_name: str, arg_names: list[str]) -> dict[str, Any]:
    """Offline grader mirroring the sandbox pytest contract: exec module, run cases."""
    hits = ast_import_bans(code)
    if hits:
        return {"passed": False, "score": 0.0, "details": {"banned_imports": hits}}
    namespace: dict[str, Any] = {}
    try:
        exec(compile(code, "<solution>", "exec"), namespace)  # noqa: S102 - sandboxed grader path
    except Exception as e:  # noqa: BLE001
        return {"passed": False, "score": 0.0, "details": {"exec_error": str(e)}}
    fn = namespace.get(fn_name)
    if not callable(fn):
        return {"passed": False, "score": 0.0, "details": {"missing_function": fn_name}}
    passed = 0
    for case in cases:
        argv = [case.get(a) for a in arg_names]
        try:
            got = fn(*argv)
            expected_val = case.get("expected")
            if expected_val is None:
                continue
            passed += int(abs(float(got) - float(expected_val)) < 1e-6)
        except Exception:  # noqa: BLE001
            pass
    score = passed / len(cases) if cases else 0.0
    return {"passed": score >= 0.6, "score": score, "details": {"passed": passed, "total": len(cases)}}


def numeric_answer_check(artifact: dict[str, Any], expected: float, tol: float) -> dict[str, Any]:
    """data_analyst: |got-expected| <= tol*|expected| and method field present."""
    try:
        raw_answer = artifact.get("answer")
        got = float(str(raw_answer))
    except (TypeError, ValueError):
        return {"passed": False, "score": 0.0, "details": {"error": "answer missing/not numeric"}}
    ok = abs(got - expected) <= tol * abs(expected)
    method = bool(artifact.get("method"))
    return {"passed": bool(ok and method), "score": 1.0 if (ok and method) else 0.0, "details": {"got": got, "expected": expected}}


def row_hash_f1(artifact: dict[str, Any], expected: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    """ops_clerk: row-hash set F1 (VERIFIERS S5)."""
    got = artifact.get("rows") or []
    exp_set = {json.dumps(r, sort_keys=True) for r in expected}
    got_set = {json.dumps(r, sort_keys=True) for r in got}
    tp = len(exp_set & got_set)
    precision = tp / len(got_set) if got_set else 0.0
    recall = tp / len(exp_set) if exp_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"passed": f1 >= threshold, "score": f1, "details": {"f1": f1, "tp": tp}}
