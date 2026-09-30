# AgentVille - Master TODO (155 subtasks)

Every box is ticked ONLY after its Verify command actually passed (rule R2). Src = doc section to
re-read before coding (rule R1). One task = one commit `T<id>: title` (rule R3). Inventions go to
DECISIONS.md (rule R4). Blockers get a [!] mark and a DECISIONS entry (rule R5). Gates block the
next phase (rule R6). Tests written from acceptance criteria before code (rule R7).

## Progress dashboard (update after every task)

```
P0 [12/12] P1 [ 0/28] P2 [ 0/21] P3 [ 0/20] P4 [ 0/12] P5 [ 0/9] P6 [ 0/31] P7 [ 0/13] P8 [ 0/9]
Overall: [12/155]   ** GATE 0 PASSED (make gate PHASE=0: 24 tests) **
```

Environment: Node 26 + uv available; Docker NOT installed (needed from P3 - see SKILLS.md checklist).

---

## Phase 0 - Foundations - COMPLETE. Gate passed: `make gate PHASE=0` = 24 tests green (I1/I2/I3/I8 verified)

- [x] 0.1 pyproject.toml (deps per TRD S1), Makefile, .env.example, .gitignore - Src: T0.1, CONFIG_REFERENCE - Verify: `uv sync` resolves; `make test lint` green [COMMIT b3253a0]
- [x] 0.2 Skeleton dirs matching TRD S1 layout with __init__.py - folded into T0.1 commit b3253a0
- [x] 0.3 ruff + mypy strict config - folded into T0.1 commit b3253a0
- [x] 0.4 docker-compose.yml + GitHub Actions CI workflow - Verify: YAML parses (full `docker compose config` deferred until Docker installed [!]) [commit b3253a0]
- [x] 0.5 config.py + config/*.yaml defaults + AV_ env overrides - Src: T0.2, CONFIG_REFERENCE - Verify: `pytest tests/unit/test_config.py` (invalid YAML raises clear error; defaults load) [COMMIT 18fba36]
- [x] 0.6 rng.py DeterministicRNG - Src: TRD S5 - Verify: unit + hypothesis purpose-independence [commit 1b69c0d]
- [x] 0.7 ids.py counter IdGen - Src: TRD S5 - Verify: format/monotonic tests; 6-digit pad per D8 [commit 1b69c0d]
- [x] 0.8 clock.py injected Clock - Src: TRD S1 - Verify: unit test; banned-nondeterminism scan of engine/ = 0 hits [commit 1b69c0d]
- [x] 0.9 SQLAlchemy typed models (27 tables - doc S1 defines 27, TODO undercounted) - round-trip tests green
- [x] 0.10 Alembic 0001-0006 + triggers (idempotent IF NOT EXISTS) - `alembic upgrade head` verified in-test; append-only aborts proven
- [x] 0.11 EventLog hash chain - verify_chain True; tamper detected (I8)
- [x] 0.12 Ledger + LedgerWriter capability - hypothesis property + 10k ops conservation; I1/I2 proven

## Phase 1 - Engine core, no LLM (Gate: oracle >=90% survival @100 ticks; noop dead <=25; golden hash stable)

- [ ] 1.1 World aggregate + snapshot/restore (identical state hash) - Src: T1.1
- [ ] 1.2 presets loader - Src: T1.1, CONFIG_REFERENCE - Verify: preset YAML loads into World
- [ ] 1.3 companies/buyers funded from treasury - Src: T1.2 - Verify: buyer balances from treasury; mint event logged
- [ ] 1.4 buyer cannot overpay (job posting respects budget) - Src: TRD S7 - Verify: unit test
- [ ] 1.5 content_creator job templates - Src: T1.3, AGENT_ROLES S1 - Verify: `JobTemplate.make(rng, difficulty)` deterministic
- [ ] 1.6 JobGenerator Poisson counts - Src: TRD S3.3 - Verify: deterministic per seed; capped at max_open_per_role
- [ ] 1.7 difficulty mix 50/35/15 within 3% over 10k jobs - Src: T1.3 - Verify: statistical test
- [ ] 1.8 audit plants ~5% - Src: TRD S3.3 - Verify: rate within tolerance over 10k
- [ ] 1.9 JobBoard state machine + illegal transitions raise - Src: TRD S3.4 - Verify: transition table test
- [ ] 1.10 expiry + grace + late multiplier - Src: TRD S3.4 - Verify: deadline tests
- [ ] 1.11 property tests I6/I7 (transitions; max concurrent) - Src: BACKEND_SCHEMA S3 - Verify: hypothesis
- [ ] 1.12 ActionSpec registry (14 actions) - Src: TRD S3.7 - Verify: registry lists all actions with schemas
- [ ] 1.13 validator 6-step pipeline (exists/role/schema/preconditions/rate/idempotency) - Src: TRD S3.6 - Verify: unit per step
- [ ] 1.14 strikes only on agent fault (not precondition/provider) - Src: TRD S3.6 - Verify: classification table test
- [ ] 1.15 take_job handler - Src: TRD S3.7 - Verify: valid/invalid/wrong-role/precondition cases
- [ ] 1.16 work_on handler (artifact LLM stubbed) - Src: TRD S3.7 - Verify: energy math; progress events
- [ ] 1.17 submit_work handler - Src: TRD S3.7 - Verify: state transition; queue verification
- [ ] 1.18 write_note handler - Src: TRD S3.7 - Verify: cap 50; importance bounds
- [ ] 1.19 update_playbook handler (evidence rule stub) - Src: TRD S3.7 - Verify: version increments
- [ ] 1.20 save_skill handler (sandbox stubbed) - Src: TRD S3.7 - Verify: only saved when tests pass (stub true/false)
- [ ] 1.21 run_skill handler (sandbox stubbed) - Src: TRD S3.7 - Verify: output becomes observation
- [ ] 1.22 study_web handler (gateway stubbed) - Src: TRD S3.7 - Verify: cost 5 coins; observation set
- [ ] 1.23 buy_item handler - Src: TRD S3.7 - Verify: ledger entry; inventory updated; cannot overspend
- [ ] 1.24 rest/eat/request_exam/quit_job/noop handlers - Src: TRD S3.7 - Verify: each unit tested
- [ ] 1.25 vitals/costs dynamics (rent/food/energy regen) - Src: T1.6, AGENT_ROLES S4 - Verify: cost table tests
- [ ] 1.26 five death conditions + 5-tick grace - Src: AGENT_ROLES S5 - Verify: truth-table tests per condition
- [ ] 1.27 death frees assigned job, no penalty - Src: TRD S3.5 - Verify: job back to OPEN; I9
- [ ] 1.28 scheduler.run_tick (transaction, rollback on LedgerError, seeded order) + CLI new-world/run/inspect + golden determinism - Src: TRD S4, T1.7-T1.9 - Verify: `make demo-core` 200 ticks; two runs same seed = identical event_hash; different seed differs

## Phase 2 - LLM Gateway and Mind (Gate: 3 real-LLM agents x 100 ticks; replay hash matches; all calls logged)

- [ ] 2.1 Provider base + mock (oracle/noop/random_valid/adversarial, seeded) - Src: LLM_GATEWAY S2, PROMPTS S8
- [ ] 2.2 freellmapi adapter (httpx, OpenAI-compatible) - Src: LLM_GATEWAY S2 - Verify: fixture contract tests
- [ ] 2.3 ollama adapter - Src: LLM_GATEWAY S2 - Verify: fixture contract tests
- [ ] 2.4 priority queue (judge>decide>produce>autopsy>summarize) - Src: LLM_GATEWAY S3 - Verify: ordering test
- [ ] 2.5 token-bucket RPM/TPM + Retry-After - Src: LLM_GATEWAY S4 - Verify: simulated 429 storm loses nothing
- [ ] 2.6 circuit breaker to 15min + retire after 10x 404 - Src: LLM_GATEWAY S4 - Verify: state machine tests
- [ ] 2.7 weighted-health router + tier fallback - Src: LLM_GATEWAY S5 - Verify: failover test
- [ ] 2.8 judge distinctness (different providers per panel) - Src: LLM_GATEWAY S5 - Verify: unit
- [ ] 2.9 call_json: fences->parse->pydantic->1 repair->InvalidModelOutput - Src: LLM_GATEWAY S7 - Verify: 95% malformed fixtures repaired or cleanly rejected
- [ ] 2.10 ReplayProvider + ReplayMiss halts - Src: LLM_GATEWAY S8 - Verify: live run then replay = identical hash
- [ ] 2.11 full llm_calls logging incl failures + redact() - Src: LLM_GATEWAY S8/S10 - Verify: every attempt has row; key patterns stripped
- [ ] 2.12 cache (temp-0 / replay only) - Src: LLM_GATEWAY S6 - Verify: cache key test; no cache at temp>0
- [ ] 2.13 Jinja2 prompts decide_v1.j2 / produce_artifact - Src: PROMPTS S1-S2 - Verify: rendered snapshot tests
- [ ] 2.14 briefing builder, 8 sections, 6000-token cap - Src: TRD S8 - Verify: budget never exceeded
- [ ] 2.15 group gating A/B/C sections - Src: PROMPTS S1 - Verify: golden briefing per group
- [ ] 2.16 mind.decide -> gateway integration - Src: T2.6 - Verify: proposal executes or noop
- [ ] 2.17 malformed output -> noop/strike rules - Src: LLM_GATEWAY S7 - Verify: empty = no strike; garbage = strike
- [ ] 2.18 notebook cap 50 - Src: TRD S8 - Verify: overflow triggers summarization
- [ ] 2.19 summarize_notes merge 10 -> 2 - Src: PROMPTS S5 - Verify: keeps highest importance
- [ ] 2.20 golden briefing snapshots per group - Src: T2.5 - Verify: stored hashes match
- [ ] 2.21 token ceilings + cost accounting - Src: LLM_GATEWAY S9 - Verify: world pauses at ceiling

## Phase 3 - Verification and Sandbox (Gate: audit false-pass <5%; payment only on verified pass) [!] Docker required

- [ ] 3.1 sandbox runner docker-py hardening flags - Src: VERIFIERS S9 - Verify: escape tests pass
- [ ] 3.2 python/node/media images - Src: TRD S1 - Verify: images build
- [ ] 3.3 escape tests (network/etc-passwd/fork-bomb/loop/huge-output) - Src: TESTING - Verify: all contained
- [ ] 3.4 jsonschema structural stage - Src: VERIFIERS S2 - Verify: fuzzed invalid inputs all fail
- [ ] 3.5 content_post_v1 schema - Src: VERIFIERS S2 - Verify: schema test
- [ ] 3.6 content checks: hook/banned/required/CTA - Src: VERIFIERS S3 - Verify: per-check tests
- [ ] 3.7 duration + Flesch readability - Src: VERIFIERS S3 - Verify: band tests
- [ ] 3.8 Jaccard 3-gram dupe gates - Src: VERIFIERS S3 - Verify: gate tests
- [ ] 3.9 tag quality - Src: VERIFIERS S3 - Verify: fraction tests
- [ ] 3.10 gold set 30 good/30 bad >=95% classification - Src: VERIFIERS S10 - Verify: classifier accuracy
- [ ] 3.11 developer role hidden pytest verifier - Src: VERIFIERS S4 - Verify: pass/fail/timeout cases
- [ ] 3.12 AST import bans (os/subprocess/socket/requests) - Src: VERIFIERS S4 - Verify: malicious samples flagged
- [ ] 3.13 data_analyst/ops_clerk comparators - Src: VERIFIERS S5 - Verify: tolerance + F1 tests
- [ ] 3.14 rubric YAML anchored - Src: VERIFIERS S6 - Verify: rubric loads; anchors present
- [ ] 3.15 judge panel distinct providers, blind, seeded order - Src: VERIFIERS S6 - Verify: panel unit tests
- [ ] 3.16 median + disagreement >0.35 fail-closed - Src: VERIFIERS S6 - Verify: disagreement test
- [ ] 3.17 injection-defense tests - Src: VERIFIERS S8 - Verify: injected instructions never inflate score
- [ ] 3.18 audit plants + false-pass metric - Src: VERIFIERS S7 - Verify: <5% on gold
- [ ] 3.19 payout tiers + late mult + reputation deltas - Src: TRD S7 - Verify: table-driven tests
- [ ] 3.20 payment trigger end-to-end (no verification = no payment) - Src: BACKEND_SCHEMA S2 - Verify: integration test

## Phase 4 - Learning and Lifecycle (Gate: successors first-20-tick earnings >= gen-1, reported either way)

- [ ] 4.1 playbook versioning + evidence rule (last 3 outcomes) - Src: T4.1 - Verify: rejected without evidence
- [ ] 4.2 playbook score_at_save - Src: TRD S8 - Verify: trailing 10-job pass rate
- [ ] 4.3 save_skill runs tests in sandbox - Src: T4.2 - Verify: failing tests not saved
- [ ] 4.4 run_skill sandboxed - Src: T4.2 - Verify: runs in sandbox; uses++ 
- [ ] 4.5 skill events - Src: BACKEND_SCHEMA S5 - Verify: skill_saved/skill_run emitted
- [ ] 4.6 autopsy prompt + pipeline - Src: PROMPTS S4, T4.3 - Verify: autopsy row created on death
- [ ] 4.7 lessons must cite real event ids - Src: PROMPTS S4 - Verify: uncited lessons dropped
- [ ] 4.8 successor spawn (funds, lessons notebook, generation+1) - Src: TRD S3.5 - Verify: successor state
- [ ] 4.9 pivot rule (percentile + job surplus) - Src: AGENT_ROLES S6 - Verify: pivot conditions tests
- [ ] 4.10 controls get no lessons; learners do - Src: AGENT_ROLES S6 - Verify: group inheritance test
- [ ] 4.11 market items + effects - Src: AGENT_ROLES S3, T4.5 - Verify: effects applied
- [ ] 4.12 cannot overspend - Src: T4.5 - Verify: rejection test

## Phase 5 - Experiment 01 (Gate: 5 seeds x 150 ticks complete; replay of one seed matches)

- [ ] 5.1 experiment01.yaml preset - Src: AGENT_ROLES S8 - Verify: preset loads; 4 groups x 3 agents
- [ ] 5.2 shadow boards (per-group job copies + per-group buyer funds) - Src: AGENT_ROLES S8 - Verify: groups see identical streams
- [ ] 5.3 experiments runner multi-seed - Src: T5.2 - Verify: runs 5 worlds
- [ ] 5.4 resumable from snapshots - Src: T5.2 - Verify: kill/restart resumes
- [ ] 5.5 metrics per group/seed - Src: AGENT_ROLES S8 - Verify: metrics computed
- [ ] 5.6 Wilcoxon + effect size - Src: AGENT_ROLES S8 - Verify: stats vs scipy reference
- [ ] 5.7 survival curves + boxplots (matplotlib) - Src: AGENT_ROLES S8 - Verify: PNGs produced
- [ ] 5.8 deterministic report reports/exp01_<date>.md - Src: T5.3 - Verify: renders identically from DB twice
- [ ] 5.9 `make demo` 20-tick smoke + report - Src: AGENTS.md - Verify: demo prints report

## Phase 6 - API and Control Room (Gate: Playwright e2e start/watch/inspect/replay)

- [ ] 6.1 FastAPI app + error envelope + bearer auth - Src: API_SPEC - Verify: contract test
- [ ] 6.2 worlds routes - Src: API_SPEC - Verify: CRUD + run/pause/resume/stop/fork/replay
- [ ] 6.3 agents routes - Src: API_SPEC - Verify: detail/timeline/llm-calls/notes/autopsy/freeze
- [ ] 6.4 jobs + verifications + artifacts routes - Src: API_SPEC - Verify: hidden params gated
- [ ] 6.5 economy/leaderboard/ledger routes - Src: API_SPEC - Verify: series match DB
- [ ] 6.6 experiments report routes - Src: API_SPEC - Verify: report JSON
- [ ] 6.7 graduates routes (approve/reject/download gated) - Src: API_SPEC - Verify: confirm-id required
- [ ] 6.8 system health/providers/kill routes - Src: API_SPEC - Verify: kill halts within 1 tick
- [ ] 6.9 api/schemas.py response models - Src: API_SPEC - Verify: models exist per list
- [ ] 6.10 cursor pagination + OpenAPI - Src: API_SPEC - Verify: pagination tests
- [ ] 6.11 schemathesis contract tests - Src: TESTING - Verify: zero unexpected failures
- [ ] 6.12 WS snapshot on connect - Src: API_SPEC WS - Verify: snapshot message
- [ ] 6.13 WS per-tick deltas <100KB - Src: TRD S11 - Verify: payload size test
- [ ] 6.14 WS reconnect -> fresh snapshot - Src: UIUX S7 - Verify: integration test
- [ ] 6.15 Prometheus /metrics - Src: TRD S10 - Verify: metric names present
- [ ] 6.16 structured JSON logs - Src: TRD S10 - Verify: log fields
- [ ] 6.17 Vite + TS strict + Tailwind tokens scaffold - Src: UIUX S3, T6.3 - Verify: build passes
- [ ] 6.18 AppShell/TopBar/WorldSelector - Src: UIUX S2 - Verify: render tests
- [ ] 6.19 PlaybackControls/KillSwitch/StatusPill - Src: UIUX S4.1 - Verify: kill confirm dialog
- [ ] 6.20 Zustand liveStore + WS reducers + backoff - Src: UIUX S7 - Verify: reducer unit tests
- [ ] 6.21 TanStack Query layer + MSW mocks - Src: UIUX S7/S11 - Verify: queries resolve against MSW
- [ ] 6.22 PixiJS tilemap districts - Src: UIUX S4.1 - Verify: render smoke
- [ ] 6.23 sprites + vitals rings - Src: UIUX S4.1 - Verify: visual snapshot
- [ ] 6.24 movement tweens >=50fps @100 agents - Src: UIUX S9 - Verify: fps bench
- [ ] 6.25 death tombstone + toasts - Src: UIUX S4.1 - Verify: e2e step
- [ ] 6.26 Inspector Timeline tab - Src: UIUX S4.2 - Verify: rows expand to raw JSON
- [ ] 6.27 Decisions tab (briefing + raw LLM + verdict) - Src: UIUX S4.2 - Verify: one-click causality
- [ ] 6.28 Work + Money tabs - Src: UIUX S4.2 - Verify: ledger chart matches API
- [ ] 6.29 Memory/Playbook diff/Skills tabs - Src: UIUX S4.2 - Verify: diff viewer
- [ ] 6.30 Job Board + Verification Lab + Economy screens - Src: UIUX S4.3-4.5 - Verify: charts match API
- [ ] 6.31 Replay scrubber + compare + fork; a11y keyboard/ARIA/reduced-motion - Src: UIUX S4.6/S9 - Verify: e2e

## Phase 7 - Web study, Exams, Export (Gate: one graduate exported after approval; package reloads)

- [ ] 7.1 fetcher GET-only HTTPS allowlist - Src: SECURITY S3 - Verify: non-allowlisted blocked
- [ ] 7.2 sanitizer + 4000-char cap - Src: SECURITY S3 - Verify: scripts stripped
- [ ] 7.3 injection heuristics + flags - Src: SECURITY S3 - Verify: corpus flagged
- [ ] 7.4 cache + replay of fetches - Src: TRD S5 - Verify: replay uses cache
- [ ] 7.5 study_web action (5 coins, rate-limited) - Src: TRD S3.7 - Verify: cost + limit
- [ ] 7.6 exam runner held-out 10 tasks in sandbox - Src: AGENT_ROLES S7 - Verify: board tasks never in exams
- [ ] 7.7 graduation criteria - Src: AGENT_ROLES S7 - Verify: eligibility tests
- [ ] 7.8 pass >=8/10 and >=0.8 mean quality - Src: AGENT_ROLES S7 - Verify: threshold tests
- [ ] 7.9 packager (manifest/prompt/playbook/skills/exam report/sample events) - Src: AGENT_ROLES S7 - Verify: package tree
- [ ] 7.10 package sha256 - Src: BACKEND_SCHEMA graduates - Verify: hash matches
- [ ] 7.11 export gate + confirm-id + trigger - Src: SECURITY S5 - Verify: cannot download unless approved
- [ ] 7.12 approval UI + audit log - Src: UIUX S4.8 - Verify: e2e approve
- [ ] 7.13 download-only-when-approved - Src: API_SPEC - Verify: 403 before approval

## Phase 8 - Roles and scale (Gate: full `make test lint gate` + AGENTS.md deliverables checklist)

- [ ] 8.1 developer role templates + recipes - Src: AGENT_ROLES S1 - Verify: gold tests pass
- [ ] 8.2 data_analyst role - Src: AGENT_ROLES S1 - Verify: gold tests pass
- [ ] 8.3 ops_clerk role - Src: AGENT_ROLES S1 - Verify: gold tests pass
- [ ] 8.4 remaining roles (copywriter/researcher/translator/qa_tester/support_agent/web_designer) - Src: AGENT_ROLES S1 - Verify: gold tests pass
- [ ] 8.5 gold sets per role - Src: VERIFIERS S10 - Verify: >=95% classification
- [ ] 8.6 Postgres profile (JSON columns, rules) - Src: BACKEND_SCHEMA, T8.5 - Verify: compose profile boots
- [ ] 8.7 cost dashboards - Src: T8.6 - Verify: token series UI
- [ ] 8.8 run comparison UI - Src: T8.7 - Verify: split view
- [ ] 8.9 final replay + docs sweep + deliverables checklist - Src: AGENTS.md - Verify: replay hash identical; checklist all green
