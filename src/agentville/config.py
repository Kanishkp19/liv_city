"""Configuration: env settings and typed YAML loaders (CONFIG_REFERENCE.md)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path("config")


class Settings(BaseSettings):
    """Env-driven settings (AV_ prefix)."""

    model_config = SettingsConfigDict(env_prefix="AV_", extra="ignore")

    token: str = "change-me"
    db_url: str = "sqlite:///data/agentville.db"
    data_dir: Path = Path("./data")
    freellmapi_url: str = "http://localhost:3001/v1"
    freellmapi_key: str = ""
    ollama_url: str = "http://localhost:11434"
    daily_token_ceiling: int = 2_000_000
    sandbox_image_python: str = "agentville/sandbox-python:latest"
    sandbox_image_node: str = "agentville/sandbox-node:latest"
    sandbox_image_media: str = "agentville/sandbox-media:latest"
    log_level: str = "INFO"
    feature_web_study: bool = False
    feature_exams: bool = False
    feature_export: bool = False
    feature_media_checks: bool = False


class Energy(BaseModel):
    max: int = 100
    rest_gain: int = 30
    idle_regen: int = 5
    work_cost_per_effort: int = 5


class BuyerTopup(BaseModel):
    floor_money_supply_ratio: float = 0.8
    amount_per_buyer: int = 500


class MarketItem(BaseModel):
    id: str
    price: int = Field(ge=1)
    effect: dict[str, Any]
    roles: list[str] | None = None


class Economy(BaseModel):
    """Economy parameters (AGENT_ROLES_AND_ECONOMY.md S3)."""

    starting_funds: int = Field(ge=0)
    successor_funds: int = Field(ge=0)
    rent_per_tick: int = Field(ge=0)
    food_per_tick: int = Field(ge=0)
    auto_eat: bool = False
    energy: Energy = Energy()
    job_rewards: dict[int, int]
    job_rate: float = Field(gt=0)
    max_open_per_role: int = Field(ge=1)
    max_concurrent_jobs: int = Field(ge=1)
    deadline_ticks: dict[int, int]
    late_grace_ticks: int = 1
    late_multiplier: float = Field(gt=0, le=1)
    quality_tiers: list[list[float]]
    reputation_delta: dict[str, float]
    min_reputation_by_difficulty: dict[int, float]
    study_cost: int = Field(ge=0)
    audit_rate: float = Field(ge=0, le=1)
    buyer_topup: BuyerTopup = BuyerTopup()
    market_items: list[MarketItem] = []

    @property
    def tier_mults(self) -> list[tuple[float, float]]:
        return [(t[0], t[1]) for t in self.quality_tiers]


class ProviderCfg(BaseModel):
    """One LLM provider row (PROVIDERS file); kind selects adapter + env fallbacks."""

    id: str
    kind: Literal["freellmapi", "ollama", "mock"]
    model: str
    base_url: str | None = None  # explicit endpoint wins over env fallback
    rpm: int = Field(ge=1)
    tpm: int = Field(ge=1)
    tier: int
    judge_ok: bool = True


class RouterCfg(BaseModel):
    strategy: str = "weighted_health"
    fallback_order: list[str] = ["tier1", "tier2", "local"]
    judge_distinct_providers: bool = True


class ProvidersCfg(BaseModel):
    providers: list[ProviderCfg]
    router: RouterCfg = RouterCfg()


def _read_yaml(path: Path) -> dict[str, Any]:
    """Parse YAML with a clear error naming the file."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        msg = f"Failed to parse {path.name}: {e}"
        raise ValueError(msg) from e
    if not isinstance(data, dict):
        msg = f"{path.name} must contain a mapping at top level"
        raise ValueError(msg)
    return data


def load_economy(path: Path | None = None) -> Economy:
    """Load economy.yaml (defaults ship with the package)."""
    p = path or _default("economy.yaml")
    return Economy.model_validate(_read_yaml(p))


def load_providers(path: Path | None = None) -> ProvidersCfg:
    """Load providers.yaml."""
    p = path or _default("providers.yaml")
    return ProvidersCfg.model_validate(_read_yaml(p))


def load_roles(path: Path | None = None) -> dict[str, Any]:
    """Load roles.yaml as raw mapping (role modules validate their slice)."""
    return _read_yaml(path or _default("roles.yaml"))


def load_allowlist(path: Path | None = None) -> dict[str, Any]:
    """Load allowlist.yaml (web study gateway)."""
    return _read_yaml(path or _default("allowlist.yaml"))


def load_judges(path: Path | None = None) -> dict[str, Any]:
    """Load judges.yaml (panel config)."""
    return _read_yaml(path or _default("judges.yaml"))


def load_settings() -> Settings:
    """Build Settings from environment."""
    return Settings()


def _default(name: str) -> Path:
    local = CONFIG_DIR / name
    if local.exists():
        return local
    bundled = Path(__file__).parent / "defaults" / name
    if bundled.exists():
        return bundled
    msg = f"config file not found: {name} (looked in {CONFIG_DIR}/ and package defaults)"
    raise FileNotFoundError(msg)


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()
