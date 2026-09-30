"""World presets (CONFIG_REFERENCE, AGENT_ROLES S8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AgentSpec(BaseModel):
    role: str
    group: str = "learner"
    count: int = Field(ge=1)


class Preset(BaseModel):
    """Preset parsed from config/presets/*.yaml."""

    name: str
    districts: list[str] = Field(
        default_factory=lambda: ["housing", "office", "studio", "market", "bank", "library"]
    )
    world: dict[str, Any] = Field(default_factory=dict)
    economy_ref: str = "economy.yaml"
    agents: list[AgentSpec] = Field(default_factory=list)
    buyers: dict[str, Any] = Field(default_factory=dict)
    seeds: list[int] | None = None
    ticks: int = 150
    groups: list[dict[str, Any]] = Field(default_factory=list)
    same_job_stream_across_groups: bool = False

    @classmethod
    def load(cls, name: str, base_dir: Path | None = None) -> Preset:
        """Load and validate a preset by name (searches config/presets/)."""
        candidates = (
            [base_dir / f"{name}.yaml"] if base_dir else [Path("config/presets") / f"{name}.yaml"]
        )
        p = next((c for c in candidates if c.exists()), candidates[0])
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            msg = f"preset {name} must be a mapping"
            raise ValueError(msg)
        data.setdefault("name", name)
        return cls.model_validate(data)
