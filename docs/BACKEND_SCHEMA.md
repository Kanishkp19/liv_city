# Backend Schema

Authoritative for data. SQLAlchemy models in `src/agentville/db/models.py` must mirror this. SQLite (WAL, `PRAGMA foreign_keys=ON`) for dev; Postgres-compatible (use `JSON` type where SQLite uses TEXT). Timestamps are ISO-8601 UTC strings; `tick` is the simulation clock. Money is integer coins.

## 1. DDL
```sql
CREATE TABLE worlds (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, seed INTEGER NOT NULL, preset TEXT NOT NULL,
  tick INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL CHECK(status IN ('created','running','paused','halted','done')),
  mode TEXT NOT NULL DEFAULT 'live' CHECK(mode IN ('live','replay')),
  source_world_id TEXT REFERENCES worlds(id),          -- for replays
  config_json TEXT NOT NULL, event_hash TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE agents (
  id TEXT PRIMARY KEY, world_id TEXT NOT NULL REFERENCES worlds(id),
  role TEXT NOT NULL, generation INTEGER NOT NULL DEFAULT 1,
  parent_id TEXT REFERENCES agents(id),
  group_type TEXT NOT NULL CHECK(group_type IN ('learner','control_a','control_b','control_c')),
  status TEXT NOT NULL CHECK(status IN ('alive','dead','graduated','pivoted')),
  born_tick INTEGER NOT NULL, died_tick INTEGER, death_cause TEXT,
  model_pref TEXT, name TEXT NOT NULL, persona_seed TEXT,
  location TEXT NOT NULL DEFAULT 'housing',
  current_job_id TEXT, inventory_json TEXT NOT NULL DEFAULT '{}',
  idle_ticks INTEGER NOT NULL DEFAULT 0,
  low_energy_ticks INTEGER NOT NULL DEFAULT 0,
  negative_funds_ticks INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_agents_world_status ON agents(world_id, status);

CREATE TABLE agent_vitals (            -- one row per agent per tick (history) ; latest row = current
  agent_id TEXT NOT NULL REFERENCES agents(id), tick INTEGER NOT NULL,
  energy INTEGER NOT NULL CHECK(energy BETWEEN 0 AND 100),
  funds INTEGER NOT NULL, reputation REAL NOT NULL CHECK(reputation BETWEEN 0 AND 100),
  strikes INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (agent_id, tick)
);

CREATE TABLE ledger_entries (          -- APPEND ONLY
  id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT NOT NULL, tick INTEGER NOT NULL,
  debit_account TEXT NOT NULL, credit_account TEXT NOT NULL,
  amount INTEGER NOT NULL CHECK(amount > 0), reason TEXT NOT NULL,
  ref_type TEXT, ref_id TEXT, event_id INTEGER
);
CREATE INDEX ix_ledger_world_tick ON ledger_entries(world_id, tick);
CREATE INDEX ix_ledger_debit ON ledger_entries(world_id, debit_account);
CREATE INDEX ix_ledger_credit ON ledger_entries(world_id, credit_account);

CREATE TABLE companies (id TEXT PRIMARY KEY, world_id TEXT NOT NULL, name TEXT NOT NULL, sector TEXT NOT NULL, budget INTEGER NOT NULL);
CREATE TABLE buyers (
  id TEXT PRIMARY KEY, world_id TEXT NOT NULL, company_id TEXT NOT NULL REFERENCES companies(id),
  name TEXT NOT NULL, persona_json TEXT NOT NULL, quality_bar REAL NOT NULL CHECK(quality_bar BETWEEN 0 AND 1),
  roles_json TEXT NOT NULL                 -- roles this buyer hires
);

CREATE TABLE jobs (
  id TEXT PRIMARY KEY, world_id TEXT NOT NULL, buyer_id TEXT NOT NULL REFERENCES buyers(id),
  role TEXT NOT NULL, title TEXT NOT NULL, brief TEXT NOT NULL,
  params_json TEXT NOT NULL,             -- full params incl. hidden test data
  visible_params_json TEXT NOT NULL,
  verifier_recipe_json TEXT NOT NULL,
  reward INTEGER NOT NULL, penalty INTEGER NOT NULL DEFAULT 0, difficulty INTEGER NOT NULL CHECK(difficulty IN (1,2,3)),
  min_reputation REAL NOT NULL DEFAULT 0,
  posted_tick INTEGER NOT NULL, deadline_tick INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('open','taken','submitted','verified_pass','verified_fail','expired')),
  assigned_agent TEXT REFERENCES agents(id), taken_tick INTEGER, submitted_tick INTEGER,
  payout INTEGER, quality REAL, is_audit_plant INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_jobs_world_status ON jobs(world_id, status, role);

CREATE TABLE artifacts (
  id TEXT PRIMARY KEY, world_id TEXT NOT NULL, agent_id TEXT NOT NULL REFERENCES agents(id),
  job_id TEXT REFERENCES jobs(id), tick INTEGER NOT NULL, kind TEXT NOT NULL,   -- text|code|json|media|html
  path TEXT NOT NULL, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, meta_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE verifications (
  id TEXT PRIMARY KEY, world_id TEXT NOT NULL, job_id TEXT NOT NULL REFERENCES jobs(id),
  artifact_id TEXT NOT NULL REFERENCES artifacts(id),
  stage TEXT NOT NULL CHECK(stage IN ('structural','programmatic','judge','audit')),
  passed INTEGER NOT NULL, score REAL, details_json TEXT NOT NULL,
  sandbox_run_id TEXT, tick INTEGER NOT NULL, error TEXT
);
CREATE INDEX ix_ver_job ON verifications(job_id);

CREATE TABLE judge_votes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, verification_id TEXT NOT NULL REFERENCES verifications(id),
  model TEXT NOT NULL, rubric_version TEXT NOT NULL, score REAL NOT NULL,
  criteria_json TEXT NOT NULL, rationale TEXT, llm_call_id INTEGER
);

CREATE TABLE events (                  -- APPEND ONLY, source of truth
  id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT NOT NULL, tick INTEGER NOT NULL, seq INTEGER NOT NULL,
  type TEXT NOT NULL, agent_id TEXT, payload_json TEXT NOT NULL,
  cause_event_id INTEGER REFERENCES events(id), prev_hash TEXT NOT NULL, hash TEXT NOT NULL,
  UNIQUE(world_id, tick, seq)
);
CREATE INDEX ix_events_agent ON events(world_id, agent_id, tick);
CREATE INDEX ix_events_type ON events(world_id, type, tick);

CREATE TABLE system_events (           -- non-transactional errors/ops, survives tick rollback
  id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT, tick INTEGER, level TEXT, message TEXT, detail_json TEXT, created_at TEXT
);

CREATE TABLE actions (
  id TEXT PRIMARY KEY, world_id TEXT NOT NULL, agent_id TEXT NOT NULL REFERENCES agents(id), tick INTEGER NOT NULL,
  action TEXT NOT NULL, args_json TEXT NOT NULL, reason TEXT,
  status TEXT NOT NULL CHECK(status IN ('accepted','rejected','error','skipped')),
  reject_reason TEXT, observation TEXT, energy_cost INTEGER DEFAULT 0, coin_delta INTEGER DEFAULT 0,
  idempotency_key TEXT NOT NULL, llm_call_id INTEGER,
  UNIQUE(world_id, idempotency_key)
);

CREATE TABLE llm_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT, tick INTEGER, agent_id TEXT,
  purpose TEXT NOT NULL,   -- decide|produce_artifact|judge|autopsy|summarize_notes|exam
  call_index INTEGER NOT NULL DEFAULT 0,
  provider TEXT, model TEXT, prompt_hash TEXT NOT NULL, prompt TEXT NOT NULL, response TEXT,
  tokens_in INTEGER, tokens_out INTEGER, latency_ms INTEGER, cached INTEGER NOT NULL DEFAULT 0,
  repaired INTEGER NOT NULL DEFAULT 0, error TEXT, created_at TEXT
);
CREATE INDEX ix_llm_world_tick ON llm_calls(world_id, tick, agent_id, purpose, call_index);

CREATE TABLE memory_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL REFERENCES agents(id), tick INTEGER NOT NULL, text TEXT NOT NULL, importance INTEGER NOT NULL CHECK(importance BETWEEN 1 AND 5), archived INTEGER NOT NULL DEFAULT 0);
CREATE TABLE playbooks (id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), version INTEGER NOT NULL, body_md TEXT NOT NULL, tick INTEGER NOT NULL, score_at_save REAL, UNIQUE(agent_id, version));
CREATE TABLE skills (id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), name TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'python', code TEXT NOT NULL, tests TEXT NOT NULL, tests_passed INTEGER NOT NULL, version INTEGER NOT NULL DEFAULT 1, uses INTEGER NOT NULL DEFAULT 0, UNIQUE(agent_id, name, version));

CREATE TABLE sandbox_runs (
  id TEXT PRIMARY KEY, world_id TEXT, agent_id TEXT, tick INTEGER, purpose TEXT,   -- verify|skill_test|skill_run|exam
  image TEXT NOT NULL, cmd_json TEXT NOT NULL, exit_code INTEGER, stdout TEXT, stderr TEXT,
  cpu_ms INTEGER, mem_mb INTEGER, timed_out INTEGER NOT NULL DEFAULT 0, created_at TEXT
);

CREATE TABLE web_fetches (
  id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT, agent_id TEXT, tick INTEGER, url TEXT NOT NULL, domain TEXT NOT NULL,
  allowed INTEGER NOT NULL, http_status INTEGER, bytes INTEGER, sanitized_text TEXT, injection_flags TEXT
);

CREATE TABLE autopsies (
  id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), tick INTEGER NOT NULL, cause TEXT NOT NULL,
  summary_md TEXT NOT NULL, lessons_json TEXT NOT NULL, starter_playbook_md TEXT, successor_id TEXT REFERENCES agents(id), llm_call_id INTEGER
);

CREATE TABLE exams (id TEXT PRIMARY KEY, role TEXT NOT NULL, version INTEGER NOT NULL, tasks_json TEXT NOT NULL, pass_threshold REAL NOT NULL, held_out INTEGER NOT NULL DEFAULT 1);
CREATE TABLE exam_attempts (id TEXT PRIMARY KEY, exam_id TEXT NOT NULL REFERENCES exams(id), agent_id TEXT NOT NULL REFERENCES agents(id), tick INTEGER NOT NULL, score REAL NOT NULL, passed INTEGER NOT NULL, details_json TEXT NOT NULL);

CREATE TABLE graduates (
  id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), exam_attempt_id TEXT NOT NULL REFERENCES exam_attempts(id),
  package_path TEXT NOT NULL, package_sha256 TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending_review','approved','rejected','exported')),
  reviewed_by TEXT, reviewed_at TEXT, review_notes TEXT, exported_at TEXT
);

CREATE TABLE market_items (id TEXT PRIMARY KEY, world_id TEXT, name TEXT, price INTEGER, effect_json TEXT);
CREATE TABLE provider_health (provider TEXT PRIMARY KEY, rpm_limit INTEGER, tpm_limit INTEGER, cooldown_until TEXT, consecutive_errors INTEGER DEFAULT 0, error_rate REAL DEFAULT 0, retired INTEGER DEFAULT 0, updated_at TEXT);
CREATE TABLE snapshots (world_id TEXT NOT NULL, tick INTEGER NOT NULL, state_json TEXT NOT NULL, event_hash TEXT NOT NULL, PRIMARY KEY(world_id,tick));
CREATE TABLE experiments (id TEXT PRIMARY KEY, name TEXT, preset TEXT, seeds_json TEXT, world_ids_json TEXT, status TEXT, report_path TEXT, created_at TEXT);
```

## 2. Triggers (SQLite; port to Postgres rules)
```sql
CREATE TRIGGER ledger_no_update BEFORE UPDATE ON ledger_entries BEGIN SELECT RAISE(ABORT,'ledger is append-only'); END;
CREATE TRIGGER ledger_no_delete BEFORE DELETE ON ledger_entries BEGIN SELECT RAISE(ABORT,'ledger is append-only'); END;
CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'events are append-only'); END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'events are append-only'); END;
-- payment requires a passing programmatic verification
CREATE TRIGGER payment_requires_verification BEFORE INSERT ON ledger_entries
WHEN NEW.reason='job_payment' AND NOT EXISTS (
  SELECT 1 FROM verifications v WHERE v.job_id=NEW.ref_id AND v.stage='programmatic' AND v.passed=1)
BEGIN SELECT RAISE(ABORT,'payment without passing verification'); END;
-- graduate export requires approval
CREATE TRIGGER export_requires_approval BEFORE UPDATE OF status ON graduates
WHEN NEW.status='exported' AND (OLD.status!='approved' OR NEW.reviewed_by IS NULL)
BEGIN SELECT RAISE(ABORT,'export requires approval'); END;
```
Note: for roles whose recipe has no programmatic stage (pure judge roles), the recipe must include a `programmatic` structural-equivalent check row; the engine writes a `programmatic` row for those recipes with `passed=1` only after their mandatory rule checks pass.

## 3. Invariants (tests in `tests/property/test_invariants.py`)
| # | Invariant |
|---|---|
| I1 | For each world, sum(amount) as debit equals sum(amount) as credit (each row does both sides; total money supply constant except explicit `mint` from `treasury_mint` account, logged) |
| I2 | Agent balance never < 0 |
| I3 | ledger/events append-only (triggers) |
| I4 | Each accepted LLM-origin action links to `llm_calls` |
| I5 | Each `job_payment` has a passing verification row |
| I6 | Job status transitions only follow the state machine |
| I7 | At most `max_concurrent_jobs` assigned per agent |
| I8 | Event hash chain unbroken: `hash = sha256(prev_hash||canonical_json(row))` |
| I9 | Dead agent has no open assigned job and no further actions after `died_tick` |
| I10 | Export status requires `approved` with reviewer |

## 4. JSON column shapes
```jsonc
// jobs.verifier_recipe_json
{"stages":[{"type":"structural","schema":"content_post_v1"},
           {"type":"programmatic","checks":["duration_range","resolution","dupe_check"],"config":{"min_s":15,"max_s":45}},
           {"type":"judge","rubric":"content_hook_v1","panel":3,"min_score":0.6}],
 "quality_weights":{"programmatic":0.6,"judge":0.4}}
// events.payload_json example: payment_settled
{"job_id":"job_000123","agent_id":"agent_0007","payout":112,"quality":0.82,"late":false}
// autopsies.lessons_json
[{"lesson":"Rejected on duplicate hook; vary openers","evidence_event_ids":[551,560]}]
```

## 5. Event catalog (type -> payload keys)
`tick_started{tick}`, `job_posted{job_id,role,reward,deadline}`, `job_taken{job_id,agent_id}`, `work_progress{job_id,effort}`, `work_submitted{job_id,artifact_id}`, `verification_stage{job_id,stage,passed,score}`, `verification_done{job_id,passed,quality,flags}`, `payment_settled{...}`, `cost_applied{rent,food}`, `note_written{note_id}`, `playbook_updated{version,score}`, `skill_saved{name,version}`, `skill_run{name,ok}`, `web_fetched{url,allowed,flags}`, `item_bought{item_id,price}`, `action_rejected{action,reason,strike}`, `agent_decision_skipped{reason}`, `agent_died{cause}`, `autopsy_created{autopsy_id}`, `successor_spawned{agent_id,parent_id,pivot}`, `exam_taken{exam_id,score}`, `graduation_pending{graduate_id}`, `export_approved{graduate_id,reviewer}`, `provider_failed{provider,error}`, `invariant_violation{code}`, `tick_committed{event_hash}`.

## 6. Migrations
Alembic revisions: `0001_core` (worlds, agents, vitals, ledger, events, jobs, artifacts), `0002_verify` (verifications, judge_votes, sandbox_runs), `0003_mind` (notes, playbooks, skills, autopsies), `0004_gateway` (llm_calls, web_fetches, provider_health, actions), `0005_lifecycle` (exams, attempts, graduates, experiments, market_items, snapshots), `0006_triggers`.

## 7. Retention
`llm_calls.prompt/response` keep full for the run; a `vacuum-run` CLI compresses old runs to gzip files and keeps metadata rows. Artifacts stored on disk under `data/worlds/<id>/artifacts/<sha256[:2]>/<sha256>`.
