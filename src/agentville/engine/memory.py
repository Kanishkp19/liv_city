"""Memory ops: notebook cap+summarize, playbook versioning w/ evidence (TRD S8, T2.7, T4.1)."""

from __future__ import annotations

from typing import Any

from agentville.engine.events import EventLog


class Notebook:
    """<=50 notes; overflow merges the 10 lowest-importance into <=2 summaries."""

    CAP = 50

    def __init__(self, events: EventLog, world_id: str) -> None:
        self.notes: list[dict[str, Any]] = []
        self.events = events
        self.world_id = world_id

    def add(self, agent_id: str, tick: int, text: str, importance: int) -> None:
        """Append a note (importance 1-5); enforces the cap via summarize()."""
        self.notes.append({"agent_id": agent_id, "tick": tick, "text": text[:280], "importance": max(1, min(5, importance))})
        self.events.emit(self.world_id, tick=tick, type_="note_written", agent_id=agent_id, payload={"note_id": len(self.notes)})
        if len(self.notes) > self.CAP:
            self._summarize_overflow(agent_id, tick)

    def _summarize_overflow(self, agent_id: str, tick: int) -> None:
        """Drop the 10 lowest-importance into 1-2 merged notes (LLM hook: plain merge in v1)."""
        ordered = sorted(range(len(self.notes)), key=lambda i: (self.notes[i]["importance"], i))
        victims = ordered[:10]
        merged_text = " | ".join(self.notes[i]["text"][:60] for i in victims[:5])
        merged = {"agent_id": agent_id, "tick": tick, "text": merged_text[:280], "importance": 2}
        for i in sorted(victims, reverse=True):
            self.notes.pop(i)
        self.notes.append(merged)
        self.events.emit(self.world_id, tick=tick, type_="notes_summarized", agent_id=agent_id, payload={"merged": 10})


class PlaybookStore:
    """Versioned playbooks; updates require evidence: job ids referenced."""

    def __init__(self) -> None:
        self.versions: dict[str, list[dict[str, Any]]] = {}

    def update(self, agent_id: str, tick: int, body_md: str, evidence_job_ids: list[str], outcome_ids: set[str]) -> int:
        """New version if evidence cites >=1 known job outcome; returns version or raises."""
        if not body_md.strip():
            msg = "empty playbook"
            raise ValueError(msg)
        if not any(j in outcome_ids for j in evidence_job_ids):
            msg = "playbook update requires evidence of recent job outcomes"
            raise ValueError(msg)
        lst = self.versions.setdefault(agent_id, [])
        lst.append({"version": len(lst) + 1, "tick": tick, "body_md": body_md[:2000], "score_at_save": None})
        return len(lst)


class SkillStore:
    """Skills saved only when their tests pass in the sandbox (T4.2)."""

    def __init__(self) -> None:
        self.skills: dict[str, dict[str, Any]] = {}

    def save(self, agent_id: str, name: str, code: str, tests: str, tests_passed: bool, tick: int) -> bool:
        """Persist only passing skills; returns success."""
        if not tests_passed:
            return False
        key = f"{agent_id}:{name}"
        prev = self.skills.get(key)
        version = (prev["version"] + 1) if prev else 1
        self.skills[key] = {"agent_id": agent_id, "name": name, "code": code, "tests": tests,
                            "version": version, "uses": 0, "saved_tick": tick}
        return True

    def run(self, agent_id: str, name: str) -> bool:
        """Record a use; actual execution is sandbox's job."""
        key = f"{agent_id}:{name}"
        if key not in self.skills:
            return False
        self.skills[key]["uses"] += 1
        return True
