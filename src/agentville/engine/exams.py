"""Exams, graduation, export packaging + human approval gate (AGENT_ROLES S7)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

from agentville.engine.types import AgentState


def graduation_eligible(agent: AgentState, *, tick: int, pass_rate_last20: float, net_earnings_last30: int) -> bool:
    """alive>=40 ticks, pass rate >=0.8 over last 20, reputation>=70, net>0 over last 30."""
    return (
        agent.status == "alive"
        and tick - agent.born_tick >= 40
        and pass_rate_last20 >= 0.8
        and agent.vitals.reputation >= 70
        and net_earnings_last30 > 0
    )


def exam_pass(attempt_scores: list[float]) -> bool:
    """>=8/10 task passes and mean quality >=0.8."""
    passes = sum(1 for s in attempt_scores if s >= 0.6)
    mean = sum(attempt_scores) / len(attempt_scores) if attempt_scores else 0.0
    return len(attempt_scores) >= 10 and passes >= 8 and mean >= 0.8


def build_package(
    *,
    out_dir: Path,
    agent_id: str,
    role: str,
    system_prompt: str,
    playbook_md: str,
    skills: list[dict[str, str]],
    exam_report_md: str,
    stats: dict[str, Any],
) -> tuple[Path, str]:
    """Write the graduate package; returns (dir, sha256 of zip)."""
    pkg = out_dir / f"graduate_{agent_id}"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "manifest.json").write_text(json.dumps({
        "agent_id": agent_id, "role": role, "stats": stats, "hash": "",
    }, indent=2), encoding="utf-8")
    (pkg / "system_prompt.md").write_text(system_prompt, encoding="utf-8")
    (pkg / "playbook.md").write_text(playbook_md, encoding="utf-8")
    (pkg / "skills").mkdir(exist_ok=True)
    for s in skills:
        (pkg / "skills" / f"{s['name']}.py").write_text(s["code"], encoding="utf-8")
        (pkg / "skills" / f"test_{s['name']}.py").write_text(s.get("tests", ""), encoding="utf-8")
    (pkg / "exam_report.md").write_text(exam_report_md, encoding="utf-8")
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pkg.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(pkg))
    sha = hashlib.sha256(buf.getvalue()).hexdigest()
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    manifest["hash"] = sha
    (pkg / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return pkg, sha


def export_allowed(status: str, reviewed_by: str | None, confirm_agent_id: str, agent_id: str) -> bool:
    """Human gate: approved + reviewer + typed confirmation of the agent id."""
    return status == "approved" and reviewed_by is not None and confirm_agent_id == agent_id
