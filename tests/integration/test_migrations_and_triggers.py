"""T0.4/T0.5: alembic upgrade head creates schema; triggers enforce invariants I3/I5/I10."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import insert, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from agentville.db.models import Event, LedgerEntry, Verification, World

pytestmark = pytest.mark.phase0


def _migrated_db(tmp_path: Path) -> Engine:
    """Run alembic upgrade head against a temp file DB and return an engine."""
    from agentville.db.session import make_engine

    db_path = tmp_path / "mig.db"
    env = {**__import__("os").environ, "AV_DB_URL": f"sqlite:///{db_path}"}
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env, capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        pytest.fail(f"alembic failed:\n{r.stdout}\n{r.stderr}")
    return make_engine(f"sqlite:///{db_path}", apply_triggers=True)


def test_upgrade_head_creates_all_tables(tmp_path: Path) -> None:
    eng = _migrated_db(tmp_path)
    names = set(inspect(eng).get_table_names())
    expected = {
        "worlds", "agents", "agent_vitals", "ledger_entries", "companies", "buyers", "jobs",
        "artifacts", "verifications", "judge_votes", "events", "system_events", "actions",
        "llm_calls", "memory_notes", "playbooks", "skills", "sandbox_runs", "web_fetches",
        "autopsies", "exams", "exam_attempts", "graduates", "market_items", "provider_health",
        "snapshots", "experiments",
    }
    assert expected <= names
    eng.dispose()


def test_ledger_append_only_triggers(tmp_path: Path) -> None:
    eng = _migrated_db(tmp_path)
    with Session(eng) as s:
        s.add(World(id="w1", name="t", seed=1, preset="p", config_json="{}", created_at="2026"))
        s.flush()
        s.execute(
            insert(LedgerEntry).values(
                world_id="w1", tick=1, debit_account="treasury", credit_account="buyer:b",
                amount=10, reason="fund",
            )
        )
        s.flush()
        with pytest.raises(Exception, match="append-only"):
            s.execute(text("UPDATE ledger_entries SET amount = 999"))
        with pytest.raises(Exception, match="append-only"):
            s.execute(text("DELETE FROM ledger_entries"))


def test_events_append_only_triggers(tmp_path: Path) -> None:
    eng = _migrated_db(tmp_path)
    with Session(eng) as s:
        s.add(World(id="w1", name="t", seed=1, preset="p", config_json="{}", created_at="2026"))
        s.flush()
        s.execute(
            insert(Event).values(world_id="w1", tick=1, seq=0, type="t", payload_json="{}", prev_hash="", hash="h")
        )
        s.flush()
        with pytest.raises(Exception, match="append-only"):
            s.execute(text("UPDATE events SET type = 'x'"))


def test_payment_requires_passing_programmatic_verification(tmp_path: Path) -> None:
    eng = _migrated_db(tmp_path)
    with Session(eng) as s:
        s.execute(text("INSERT INTO worlds (id, name, seed, preset, tick, status, mode, config_json, event_hash, created_at) VALUES ('w1','t',1,'p',0,'created','live','{}','','2026')"))
        s.execute(text("INSERT INTO agents (id, world_id, role, generation, group_type, status, born_tick, name, location, inventory_json, idle_ticks, low_energy_ticks, negative_funds_ticks) VALUES ('agent_000001','w1','content_creator',1,'learner','alive',0,'A','housing','{}',0,0,0)"))
        s.execute(text("INSERT INTO companies (id, world_id, name, sector, budget) VALUES ('c1','w1','C','media',10000)"))
        s.execute(text(
            "INSERT INTO buyers (id, world_id, company_id, name, persona_json, quality_bar, roles_json)"
            " VALUES ('b1','w1','c1','B','{}',0.7,'[\"content_creator\"]')"
        ))
        s.execute(text(
            "INSERT INTO jobs (id, world_id, buyer_id, role, title, brief, params_json, visible_params_json,"
            " verifier_recipe_json, reward, penalty, difficulty, min_reputation, posted_tick, deadline_tick, status, is_audit_plant)"
            " VALUES ('job_000001','w1','b1','content_creator','t','b','{}','{}','{}',90,0,1,0,1,5,'open',0)"
        ))
        s.flush()
        # payment with no verification -> abort
        with pytest.raises(Exception, match="payment without passing verification"):
            s.execute(
                insert(LedgerEntry).values(
                    world_id="w1", tick=2, debit_account="buyer:b1", credit_account="agent:agent_000001",
                    amount=90, reason="job_payment", ref_id="job_000001",
                )
            )
        # failing programmatic verification still blocks payment
        s.execute(
            insert(Event).values(world_id="w1", tick=1, seq=0, type="seed", payload_json="{}", prev_hash="", hash="h0")
        )
        s.flush()
        s.execute(
            text(
                "INSERT INTO artifacts (id, world_id, agent_id, job_id, tick, kind, path, sha256, size_bytes, meta_json)"
                " VALUES ('art1','w1','agent_000001','job_000001',1,'text','p','aa',3,'{}')"
            )
        )
        s.execute(
            insert(Verification).values(
                id="v1", world_id="w1", job_id="job_000001", artifact_id="art1",
                stage="programmatic", passed=False, score=0.1, details_json="{}", tick=1,
            )
        )
        s.flush()
        with pytest.raises(Exception, match="payment without passing verification"):
            s.execute(
                insert(LedgerEntry).values(
                    world_id="w1", tick=3, debit_account="buyer:b1", credit_account="agent:agent_000001",
                    amount=90, reason="job_payment", ref_id="job_000001",
                )
            )
        # passing verification unlocks payment
        s.execute(text("UPDATE verifications SET passed = 1 WHERE id = 'v1'"))
        s.flush()
        s.execute(
            insert(LedgerEntry).values(
                world_id="w1", tick=4, debit_account="buyer:b1", credit_account="agent:agent_000001",
                amount=90, reason="job_payment", ref_id="job_000001",
            )
        )


def test_export_requires_approval_trigger(tmp_path: Path) -> None:
    eng = _migrated_db(tmp_path)
    with Session(eng) as s:
        s.execute(text("INSERT INTO worlds (id, name, seed, preset, tick, status, mode, config_json, event_hash, created_at) VALUES ('w1','t',1,'p',0,'created','live','{}','','2026')"))
        s.execute(text("INSERT INTO agents (id, world_id, role, generation, group_type, status, born_tick, name, location, inventory_json, idle_ticks, low_energy_ticks, negative_funds_ticks) VALUES ('agent_000001','w1','content_creator',1,'learner','alive',0,'A','housing','{}',0,0,0)"))
        s.flush()
        s.execute(text("INSERT INTO exams (id, role, version, tasks_json, pass_threshold, held_out) VALUES ('e1','content_creator',1,'{}',0.8,1)"))
        s.execute(text(
            "INSERT INTO exam_attempts (id, exam_id, agent_id, tick, score, passed, details_json)"
            " VALUES ('ea1','e1','agent_000001',1,0.9,1,'{}')"
        ))
        s.execute(text(
            "INSERT INTO graduates (id, agent_id, exam_attempt_id, package_path, package_sha256, status)"
            " VALUES ('g1','agent_000001','ea1','/tmp/pkg','abc','pending_review')"
        ))
        s.flush()
        # approve without reviewer -> abort (must set reviewed_by in same statement)
        with pytest.raises(Exception, match="export requires approval"):
            s.execute(text("UPDATE graduates SET status='exported' WHERE id='g1'"))
        # approved with reviewer first, then export -> ok
        s.execute(text("UPDATE graduates SET status='approved', reviewed_by='kanishk' WHERE id='g1'"))
        s.execute(text("UPDATE graduates SET status='exported' WHERE id='g1'"))
        s.flush()
