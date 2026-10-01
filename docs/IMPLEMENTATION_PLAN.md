# Implementation Plan

Each task: **ID, deliverable, files, acceptance criteria (AC)**. Implement in order; write tests from ACs first. `make gate PHASE=n` runs that phase's gate tests. One task = one commit (`T<id>: title`).

## Phase 0: Foundations
| ID | Task | AC |
|---|---|---|
| T0.1 | Scaffold repo: `pyproject.toml` (ruff, mypy strict, pytest), Makefile (`test lint gate demo up down`), `docker-compose.yml` (api, control-room, db volume), `.env.example`, CI workflow | `make lint test` runs green on empty tests; `docker compose config` valid |
| T0.2 | `config.py`, YAML loaders for `config/*.yaml` with pydantic validation | Invalid YAML raises clear error; defaults from CONFIG_REFERENCE.md load |
| T0.3 | `rng.py`, `ids.py`, `clock.py` | Same inputs -> same outputs across runs; property test on independence between purposes |
| T0.4 | DB models + Alembic 0001-0006 from BACKEND_SCHEMA.md incl. triggers | `alembic upgrade head` creates all tables; trigger tests: UPDATE/DELETE on ledger/events abort |
| T0.5 | `EventLog` with hash chain | Chain verifies; tampering test fails verification |
| T0.6 | `Ledger` + `LedgerWriter` capability | Property test (hypothesis, 10k random ops): conservation, no negative agent balance, reconcile passes |
**Gate 0:** T0.x tests green; invariants I1-I3, I8 pass.

## Phase 1: Engine core (no LLM)
| T1.1 | `World` aggregate, snapshot/restore, presets loader | Snapshot -> restore -> identical state hash |
| T1.2 | `market.py`: companies, buyers, funding from treasury | Buyers funded; buyer can't overpay |
| T1.3 | `JobGenerator` + template registry (content_creator first) | Deterministic for seed; difficulty mix within 3% over 10k; audit rate ~5% |
| T1.4 | `JobBoard` state machine | Illegal transitions raise; expiry works; I6, I7 property tests |
| T1.5 | Action registry + validator + handlers (all actions in TRD 3.7 except LLM-dependent effects stubbed) | Each handler has unit tests for valid, invalid schema, wrong role, precondition failure; strikes only on agent-fault |
| T1.6 | `lifecycle.py`: costs, vitals, death rules, grace period | Death rule table tests (all 5 conditions); dead agent frees job |
| T1.7 | `scheduler.run_tick` with scripted agents (mock `oracle`, `noop`, `random_valid`, `adversarial`) | Transaction rollback on injected LedgerError; tick deterministic |
| T1.8 | CLI: `new-world`, `run`, `inspect`, `events` | `make demo-core` runs 200 ticks headless and prints summary |
| T1.9 | Golden determinism test | Two runs same seed -> identical event_hash; changing seed changes it |
**Gate 1:** oracle agents survive >=90% of 100 ticks; noop agents die by tick 25; adversarial agents never change balances illegitimately; golden hash stable.

## Phase 2: LLM Gateway and Mind
| T2.1 | Provider base + mock + freellmapi + ollama adapters | Contract tests against recorded fixtures |
| T2.2 | Queue, rate limiter, circuit breaker, router, cache | Simulated 429 storms don't lose requests; priority order verified |
| T2.3 | `call_json` with repair | 95% of malformed fixtures repaired or cleanly rejected |
| T2.4 | Replay provider and `llm_calls` logging | Live run then replay -> identical hash; ReplayMiss halts |
| T2.5 | Briefing builder with token budgets, group gating | Golden briefing snapshots per group; budget never exceeded |
| T2.6 | `mind.decide` + action gateway integration | Malformed output -> noop/strike per rules |
| T2.7 | Notebook memory + summarization | Cap 50 enforced; summary keeps highest importance |
**Gate 2:** 3 real-LLM agents run 100 ticks without engine error; replay matches; all LLM calls logged.

## Phase 3: Verification and Sandbox
| T3.1 | Sandbox runner + images (python, node, media) | Escape tests: no network, no write outside /work, fork bomb capped, timeout kill |
| T3.2 | Structural stage + schemas | Fuzzed invalid inputs all fail |
| T3.3 | Content programmatic checks (VERIFIERS.md 3) | Gold set: >=95% correct classification |
| T3.4 | Developer role + pytest verifier | Malicious solutions (network, file writes) fail safely |
| T3.5 | Judge panel + rubrics + aggregation + disagreement fail-closed | Injection samples don't inflate score; disagreement flagged |
| T3.6 | Audit plants + false-pass metrics | Measured false-pass < 5% on gold |
| T3.7 | Payment settlement + tier math + reputation | Table-driven tests of payout formula; trigger blocks unpaid verification |
**Gate 3:** audit false-pass < 5%; end-to-end job pays only when verified.

## Phase 4: Learning and Lifecycle
| T4.1 | Playbook versioning + evidence requirement | Update rejected without cited outcomes |
| T4.2 | Skills save/run in sandbox with tests | Failing tests -> not saved |
| T4.3 | Autopsy pipeline + lesson evidence validation | Lessons w/o valid event ids dropped |
| T4.4 | Successor/pivot logic, group-specific inheritance | Controls get no lessons; learners do |
| T4.5 | Market items and purchases | Effects applied; can't overspend |
**Gate 4:** run with learners shows successors' first-20-tick earnings >= first-gen (soft target; report even if not met).

## Phase 5: Experiment 01
| T5.1 | Preset `experiment01.yaml` + shadow boards | Groups see identical job streams |
| T5.2 | `experiments` runner (multi-seed, resumable) | Kill/restart resumes from last snapshot |
| T5.3 | Report generator (survival curves, earnings, ablation, stats) | Report renders deterministically from DB |
**Gate 5:** 5 seeds x 150 ticks complete with free-tier providers; report produced; replay of one seed matches.

## Phase 6: API and Control Room
| T6.1 | FastAPI routes per API_SPEC.md + schemas + auth | OpenAPI validates; contract tests |
| T6.2 | WebSocket streaming with snapshot + deltas | Reconnect gets snapshot; payload <100KB/tick |
| T6.3 | Frontend scaffold (Vite, TS strict, Tailwind, Zustand, TanStack Query) + design tokens | Builds; Storybook/preview of components optional |
| T6.4 | Live City map (PixiJS) | 100 agents at >=50fps |
| T6.5 | Agent Inspector (tabs, timeline, prompt viewer, playbook diff) | Every number links to an event |
| T6.6 | Economy, Job Board, Verification Lab screens | Charts match API values |
| T6.7 | Replay with scrubber, speed, compare runs | Jump-to-event works |
| T6.8 | Experiment report screen, System Health, kill switches | Kill switch halts engine within 1 tick |
**Gate 6:** Playwright e2e: start experiment, watch, inspect death, replay.

## Phase 7: Web study, Exams, Export
| T7.1 | Web gateway (allowlist, GET-only, size cap, sanitizer, injection heuristics, cache/replay) | Injection corpus flagged; non-allowlisted blocked |
| T7.2 | `study_web` action | Costs coins; result sanitized |
| T7.3 | Exams runner + graduation criteria | Held-out tasks never on board |
| T7.4 | Packager + export gate + approval UI | Cannot download unless approved; confirm-id required |
**Gate 7:** one graduate exported after approval; package reload test.

## Phase 8: Roles and scale
T8.1 developer, T8.2 data_analyst, T8.3 ops_clerk, T8.4 remaining roles each with templates, verifiers, gold sets. T8.5 Postgres profile. T8.6 cost dashboards. T8.7 run comparison.

## Build order shortcuts
Frontend can start at Phase 2 against mock API (MSW). Keep API stable per API_SPEC.md.

## Risks and fallbacks
Free API instability -> increase caching, lower agent count, use local model for decide only. Verifier gaming -> rotate hidden tests, tighten audits. Long ticks -> reduce concurrency contention, prefer paced mode.
