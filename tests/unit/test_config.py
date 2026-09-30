"""T0.2 acceptance: config loading, validation errors, env overrides."""

from __future__ import annotations

from pathlib import Path

from agentville.config import load_economy, load_providers, load_settings

FIX = Path(__file__).parent / "fixtures"


def test_default_yaml_loads_with_defaults() -> None:
    eco = load_economy()
    assert eco.rent_per_tick == 20
    assert eco.food_per_tick == 10
    assert eco.job_rewards == {1: 40, 2: 90, 3: 200}
    assert eco.job_rate == 1.5
    assert eco.audit_rate == 0.05
    assert eco.max_concurrent_jobs == 1
    assert eco.deadline_ticks == {1: 4, 2: 6, 3: 10}
    assert eco.quality_tiers == [[0.9, 1.25], [0.75, 1.0], [0.6, 0.6], [0.0, 0.0]]


def test_providers_yaml_loads() -> None:
    provs = load_providers()
    assert len(provs.providers) == 4
    assert provs.router.judge_distinct_providers is True


def test_invalid_yaml_raises_clear_error(tmp_path: Path) -> None:
    bad = tmp_path / "economy.yaml"
    bad.write_text("rent_per_tick: [unclosed", encoding="utf-8")
    try:
        load_economy(bad)
    except Exception as e:  # noqa: BLE001
        assert "economy.yaml" in str(e) or "parse" in str(e).lower()
    else:
        raise AssertionError("invalid YAML must raise")


def test_invalid_values_raise_validation_error(tmp_path: Path) -> None:
    bad = tmp_path / "economy.yaml"
    bad.write_text("rent_per_tick: -5", encoding="utf-8")
    try:
        load_economy(bad)
    except Exception:
        pass
    else:
        raise AssertionError("negative rent must fail validation")


def test_env_override(tmp_path: Path, monkeypatch: object) -> None:  # noqa: ARG001
    import os

    os.environ["AV_DAILY_TOKEN_CEILING"] = "123"
    try:
        s = load_settings()
        assert s.daily_token_ceiling == 123
    finally:
        os.environ.pop("AV_DAILY_TOKEN_CEILING", None)
