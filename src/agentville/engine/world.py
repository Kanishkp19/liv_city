"""World aggregate: in-memory engine state synced with DB; snapshots restore identically (T1.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from agentville.clock import Clock
from agentville.config import Economy
from agentville.engine.types import AgentState, Coins
from agentville.ids import IdGen
from agentville.rng import derive_rng


@dataclass
class World:
    """Everything the engine needs for one simulated city."""

    id: str
    name: str
    seed: int
    preset: str
    tick: int = 0
    economy: Economy | None = None
    config: dict[str, Any] = field(default_factory=dict)
    agents: dict[str, AgentState] = field(default_factory=dict)
    # account -> coins, mirrored to ledger; cached for fast checks
    accounts: dict[str, Coins] = field(default_factory=dict)
    clock: Clock = field(default_factory=Clock)
    ids: IdGen = field(default_factory=IdGen)
    event_hash: str = ""

    def rng(self, purpose: str, agent_id: str | None = None) -> Any:
        """Deterministic RNG for this world/tick/purpose (AGENTS.md rule 4)."""
        return derive_rng(self.seed, self.tick, purpose, agent_id)

    def alive_agents(self) -> list[AgentState]:
        return [a for a in self.agents.values() if a.status == "alive"]

    def agents_by_role(self, role: str) -> list[AgentState]:
        return [a for a in self.alive_agents() if a.role == role]

    def snapshot(self) -> dict[str, Any]:
        """Deterministic state dict; equal states give equal hashes."""
        return {
            "id": self.id,
            "name": self.name,
            "seed": self.seed,
            "preset": self.preset,
            "tick": self.tick,
            "event_hash": self.event_hash,
            "config": self.config,
            "agents": {
                aid: json.loads(a.model_dump_json())
                for aid, a in sorted(self.agents.items())
            },
            "accounts": dict(sorted(self.accounts.items())),
        }

    def snapshot_json(self) -> str:
        return json.dumps(self.snapshot(), sort_keys=True, separators=(",", ":"))

    def restore(self, state: dict[str, Any]) -> None:
        """Restore from snapshot(); restored world hashes identically."""
        self.id = state["id"]
        self.name = state["name"]
        self.seed = state["seed"]
        self.preset = state["preset"]
        self.tick = state["tick"]
        self.event_hash = state["event_hash"]
        self.config = state["config"]
        self.accounts = dict(state["accounts"])
        self.agents = {
            aid: AgentState.model_validate(a)
            for aid, a in state["agents"].items()
        }
        self.clock = Clock(tick=self.tick)
        ids = IdGen()
        for _ in self.agents:
            ids.next("agent")
        self.ids = ids

    def state_hash(self) -> str:
        """sha256 of the canonical snapshot."""
        import hashlib

        return hashlib.sha256(self.snapshot_json().encode("utf-8")).hexdigest()
