# AgentVille — Skill Inventory (SKILLS.md)

Generated from a full read of all 16 spec files: AGENTS.md, README.md, PRD.md, TRD.md, BACKEND_SCHEMA.md,
API_SPEC.md, AGENT_ROLES_AND_ECONOMY.md, VERIFIERS.md, PROMPTS.md, LLM_GATEWAY.md, SECURITY_AND_SAFETY.md,
TESTING.md, CONFIG_REFERENCE.md, UIUX_BRIEF.md, IMPLEMENTATION_PLAN.md, DECISIONS.md.

How to read: each skill lists **what** it is, **why** (source doc + section), and **when** (implementation
phase from IMPLEMENTATION_PLAN.md). Group M lists the MCP servers that support this build and why each was
chosen. Skill IDs (e.g. `B6`) are referenced from `mcp_servers.json` rationale and DECISIONS.md D6.

---

## A. Spec & process discipline

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| A1 | Spec-driven development with doc precedence | BACKEND_SCHEMA.md wins for data, TRD for behavior, API_SPEC for wire formats; no ambiguity survives undocumented | AGENTS.md | 0–8 |
| A2 | Acceptance-criteria-first TDD | Write tests from each task's AC **before** implementing; green is the only exit | AGENTS.md, IMPLEMENTATION_PLAN.md | all |
| A3 | Phase-gate discipline | `make gate PHASE=n` must be green before starting the next phase | AGENTS.md | each |
| A4 | Assumption & decision logging | Smallest reasonable assumption, recorded in DECISIONS.md; one task = one commit `T<id>: <title>` | AGENTS.md, DECISIONS.md | all |
| A5 | Glossary fluency | Correct use of: tick, vitals, playbook, skill, autopsy, successor, pivot, graduate, audit plant, shadow board, fail closed, LedgerWriter, ReplayMiss | README.md | all |

## B. Python 3.12 core engineering

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| B6 | Modern typing | StrEnum, `X \| None`, Protocol, Literal; every public function typed + one-line docstring; mypy --strict clean | AGENTS.md, TRD §2 | 0–8 |
| B7 | Pydantic v2 domain modeling | Coins=int, Vitals, AgentState, JobSpec, Proposal, ActionResult, LLMRequest/Response, StageResult, VerificationResult | TRD §2, §6; LLM_GATEWAY §1 | 0–2 |
| B8 | pydantic-settings + YAML config | `config.py` loading config/*.yaml with clear validation errors; `AV_` env overrides; feature flags | CONFIG_REFERENCE, T0.2 | 0 |
| B9 | SQLAlchemy 2.x typed models | Mirror the 24-table DDL exactly (worlds, agents, agent_vitals, ledger_entries, events, jobs, artifacts, verifications, judge_votes, llm_calls, actions, etc.) | BACKEND_SCHEMA §1 | 0 |
| B10 | Alembic migrations + SQLite triggers | 0001_core→0006_triggers; append-only ledger/events triggers; payment-requires-verification; export-requires-approval | BACKEND_SCHEMA §2, §6, T0.4 | 0 |
| B11 | asyncio engineering | bounded `gather`, PriorityQueue, per-call timeouts, single-writer state mutation, worker pools | TRD §4, LLM_GATEWAY §3 | 1–2 |
| B12 | httpx async clients | FreeLLMAPI (OpenAI-compatible) and Ollama adapters; recorded-fixture contract tests; no SDKs outside providers/ | LLM_GATEWAY §2, §11 | 2 |
| B13 | Typer CLI | new-world, run, inspect, replay, report, export, vacuum-run | TRD §1, CONFIG_REFERENCE | 1+ |
| B14 | Jinja2 versioned prompts | all prompts in `mind/prompts/*.j2` with version suffixes; never inline in code | PROMPTS.md | 2+ |
| B15 | jsonschema validation | structural stage schemas like `content_post_v1`; fuzzed invalid inputs must fail | VERIFIERS §2 | 3 |
| B16 | Lint & typing hygiene | ruff + mypy --strict on engine/gateway/verifier; ESLint + tsc for frontend | AGENTS.md | all |

## C. Determinism & engine architecture

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---| targets |
|---|---|---|---|---|
| C17 | Seeded deterministic RNG | `Random(sha256("seed:tick:purpose:agent_id"))`; zero use of `random`/`time.time()`/`uuid4` in engine; property test purpose-independence | TRD §5, T0.3 | 0 |
| C18 | Counter-based IdGen + injected Clock | `agent_0007`, `job_000123` style ids per world; wall clock only for created_at | TRD §1, §5 | 0 |
| C19 | Hash-chained event log | `hash = sha256(prev_hash + canonical_json(event))`; tamper test fails verification; rolling hash in snapshots | TRD §3.2, I8, T0.5 | 0 |
| C20 | Double-entry integer-coin ledger | post/balance/reconcile; raises on amount≤0 and negative agent balances; LedgerWriter capability object (not importable globally) | TRD §3.1, T0.6 | 0 |
| C21 | World aggregate + snapshot/restore | snapshot→restore→identical state hash; snapshots keyed (world_id, tick) | T1.1 | 1 |
| C22 | 10-step tick algorithm | expire→generate→order→gather(bounded)→apply→verify→settle→costs→deaths→market→reconcile→snapshot; per-tick transaction; rollback on LedgerError; system_events survives rollback | TRD §4, T1.7 | 1 |
| C23 | JobBoard state machine | OPEN→TAKEN→SUBMITTED→verified_pass/verified_fail; deadline→EXPIRED; illegal transitions raise; grace + late multiplier | TRD §3.4, I6 | 1 |
| C24 | JobGenerator calibration | Poisson(λ = job_rate × alive-in-role), 50/35/15 difficulty mix within 3%, audit plants ~5%, per-group shadow boards with buyer funds per group | TRD §3.3, §8, T1.3, T5.1 | 1, 5 |
| C25 | Action gateway pipeline | parse JSON (1 repair) → exists/role/schema/preconditions/rate/idempotency → handler → events + observation; strikes only for agent-fault rejections | TRD §3.6, T1.5 | 1–2 |
| C26 | Lifecycle engine | energy/rent/food dynamics; 5 death conditions (first match wins) + 5-tick grace; freeze-and-release jobs on death; evidence-cited autopsies; same-role/pivot succession with group-specific inheritance (controls get no lessons) | TRD §3.5, AGENT_ROLES §4–6, T1.6, T4.3–4.4 | 1, 4 |
| C27 | Replay determinism | ReplayProvider keyed (world, tick, agent, purpose, call_index); sandbox runs and web fetches recorded+replayed; ReplayMiss halts (no silent live calls) | TRD §5, LLM_GATEWAY §8, T2.4 | 2 |
| C28 | Market simulation | companies/buyers funded from treasury; top-up rule; buyer can't overpay; market items with effect application and overspend prevention | TRD §2, §7, T1.2, T4.5 | 1, 4 |

## D. Verification engineering

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| D29 | Fixed stage pipeline, fail-closed | structural→programmatic→judge→audit; any stage error ⇒ passed=False, flag `verifier_error` | VERIFIERS §1, SECURITY §4 | 3 |
| D30 | Content programmatic checks | hook ≤12 words, banned/required terms, CTA gate, duration estimate at 2.5 wps, Flesch readability band, Jaccard 3-gram dupe gates (personal <0.5, global <0.6), tag quality; score = mean(fractions) only if all gates pass | VERIFIERS §3, T3.3 | 3 |
| D31 | Code & data verifiers | hidden pytest in sandbox (≥60% gate, no timeout/crash) + AST import bans; numeric tolerance compare; CSV row-hash F1 ≥ 0.9 | VERIFIERS §4–5, T3.4 | 3, 8 |
| D32 | Judge panel engineering | 3 distinct providers, identity-blind, seeded order randomization, median aggregate, disagreement >0.35 ⇒ fail closed + owner review, anchored rubric YAML | VERIFIERS §6, T3.5 | 3 |
| D33 | Audit plants & gold sets | hold-out good/bad artifacts injected into the verifier queue; false-pass <5% metric over last 100 audits; 30 good + 30 bad content golds; malicious dev solutions | VERIFIERS §7, §10, T3.6 | 3 |
| D34 | Payout & reputation math | base × tier_mult(0.9/0.75/0.6 cutoffs) × late_mult(0.7); floor(); rep deltas ±; DB trigger blocks payment without passing verification | TRD §7, T3.7 | 3 |

## E. LLM gateway craft

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| E35 | Provider abstraction & router | base Provider protocol; weighted-health routing; model_hint respected; tiered fallback to local; judge distinctness | LLM_GATEWAY §2, §5 | 2 |
| E36 | Rate limiting & circuit breaking | token-bucket RPM/TPM (60s window), Retry-After on 429, cooldown, exponential circuit open to 15 min, retirement after 10× 404 | LLM_GATEWAY §4 | 2 |
| E37 | Structured-output hardening | json_mode → strip fences → json.loads → pydantic → 1 repair retry (temp 0.2) → InvalidModelOutput; strike only if response was non-empty | LLM_GATEWAY §7, PROMPTS §1 | 2 |
| E38 | Priority queue & scheduling | judge 0 > decide 1 > produce 2 > autopsy 3 > summarize 4; worker pool = min(provider concurrency, 4); 30s timeout ⇒ skip as noop, no strike | LLM_GATEWAY §3, TRD §4 | 2 |
| E39 | Cache + full-call logging | cache only at temperature 0 or replay; sha256 provider-agnostic key; every attempt logged incl. failures; redact() on prompts | LLM_GATEWAY §6, §8, §10 | 2 |
| E40 | Token accounting & ceilings | per agent/purpose/world; "cost per job" in reports; per-world daily ceiling pauses world with alert | LLM_GATEWAY §9 | 2, 5 |
| E41 | Mock provider policies | oracle (reference solver), noop, random_valid, adversarial (invalid actions, injection strings, tampering); seeded and used in CI + calibration | PROMPTS §8, TESTING | 1–3 |

## F. Prompting & agent cognition

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| F42 | Briefing builder with token budgets | hard 6,000-token cap across 8 sections (system 600, vitals 300, jobs 900, active job 500, observations 800, notebook 700, playbook 500, skills 200); group gating zeroes sections for A/B/C | TRD §8, PROMPTS §1, T2.5 | 2 |
| F43 | Injection-resistant prompt design | `<untrusted>` delimiters as data boundaries; judge told to ignore in-artifact instructions; injection flags ⇒ score 0 | PROMPTS §3, VERIFIERS §8 | 2–3 |
| F44 | Memory prompt ops | autopsy schema with evidence-cited lessons (validated against real event ids); note summarization (10 lowest → ≤2); playbook evidence requirement (last 3 job outcomes) | PROMPTS §4–5, TRD §8, T4.1, T4.3 | 2, 4 |

## G. Security & sandbox

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| G45 | Hardened Docker sandbox runner | docker-py: `--network none --read-only --tmpfs /work:rw,size=64m --user 65534 --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 0.5`; output ≤64KB; container always removed; results in sandbox_runs | VERIFIERS §9, T3.1 | 3 |
| G46 | Minimal pinned images | python/node/media images with no extra shell utilities; pinned tags | VERIFIERS §9, TRD §1 | 3 |
| G47 | Threat-model testing | map S1–S11 to control + adversarial test (tampering, gaming, escape, injection, exfiltration, secrets, runaway, export gate, collusion, PII, API abuse) | SECURITY §2, TESTING | 3, 7 |
| G48 | Web study gateway | GET-only HTTPS allowlist (registrable domain), ≤2 redirects, 1MB cap, HTML→text sanitize, 4000-char truncate, injection heuristics, per-agent rate limit, cache+replay | SECURITY §3, T7.1–7.2 | 7 |
| G49 | Human export gate | graduates status machine (pending_review→approved→exported), confirm-by-typing-agent-id, DB trigger backstop, immutable audit log, download only when approved | SECURITY §5, T7.4 | 7 |
| G50 | Kill switches | per-agent freeze, provider disable, web gateway disable, world pause, global stop — all API+UI exposed and logged; halt within 1 tick | SECURITY §6, US9, T6.8 | 6–7 |
| G51 | Secret hygiene | keys only inside providers, `redact()` strips key patterns from prompts/logs, no keys in DB | LLM_GATEWAY §10, S6 | 2+ |

## H. API & realtime

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| H52 | FastAPI REST craft | error envelope `{error:{code,message,details}}`, cursor pagination, bearer auth, OpenAPI-validated schemathesis contract tests, response models in api/schemas.py | API_SPEC, T6.1 | 6 |
| H53 | WebSocket streaming | snapshot-then-delta messages; batch per tick; <100KB/tick; reconnect ⇒ fresh snapshot; subscribe/speed client messages | API_SPEC §WS, T6.2 | 6 |
| H54 | Observability | structured JSON logs keyed world/tick/agent/event_id; Prometheus /metrics (tick_duration, llm_queue_depth, verifier_pass_ratio, agents_alive, money_supply…) | TRD §10 | 6 |

## I. Frontend Control Room

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| I55 | React+Vite+TS strict scaffold | 8 routes, design tokens (--bg #0E1116 etc.), desktop-first ≥1280px, left-rail shell + top bar + event drawer | UIUX §1–3, T6.3 | 6 |
| I56 | PixiJS 8 city canvas | district tilemap (Housing/Office/Studio/Market/Bank/Library), sprites with role colors + vitals rings, 400ms tweens, ≥50fps at 100 agents, tombstone death animation, reduced-motion | UIUX §4.1, §9, T6.4 | 6 |
| I57 | Live state & data layer | Zustand liveStore (snapshot→tick deltas, 500-event ring buffer, backoff reconnect 1s→15s); TanStack Query for history (stale 5s live / ∞ replays); MSW mock API; react-virtual | UIUX §7, §11 | 6 |
| I58 | Charts & viewer components | Recharts survival curves (KM-style), earnings boxplots, time series, sparklines; DiffViewer, JsonViewer, StageCard, JudgeVotes, PackageTree, ConfirmTypeModal, toasts (~35 components) | UIUX §4, §6, T6.5–6.8 | 6 |
| I59 | A11y & e2e | WCAG AA, full keyboard nav (space/[/]//g+l shortcuts), ARIA live toasts, Storybook/Ladle, Playwright e2e for 4 key flows, visual regression | UIUX §9, §11 | 6 |

## J. Data & experimentation

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| J60 | Multi-seed experiment runner | 5 seeds × 4 groups × 150 ticks; resumable from snapshots after kill/restart | AGENT_ROLES §8, T5.2 | 5 |
| J61 | Statistical analysis & charts | Wilcoxon signed-rank paired across seeds, Kaplan–Meier survival, OLS quality slope, boxplots; matplotlib PNGs + CSV; deterministic markdown report | AGENT_ROLES §8, T5.3 | 5 |
| J62 | Economy calibration suite | oracle ≥90% survival @100 ticks, mediocre 30–70%, noop ≤25, random ≤40; fails CI on drift; judge drift nightly | TESTING calibration, AGENT_ROLES §3 | 1, 5 |

## K. DevOps & delivery

| # | Skill | What it means in practice | Source | Phase |
|---|---|---|---|---|
| K63 | Compose + Makefile | docker-compose (api, control-room, db volume, sandbox builds); make up/down/test/lint/gate/demo/demo-core/calibrate/frontend/e2e/clean | CONFIG_REFERENCE, T0.1 | 0+ |
| K64 | CI pipeline | GitHub Actions: lint→unit/property→golden→integration(docker)→adversarial→frontend; nightly calibration + judge drift; coverage ≥85% engine/gateway/verifier; pytest-socket (no network tests) | TESTING CI, T0.1 | 0 |
| K65 | Frontend build & Postgres profile | Vite build, ESLint+tsc, bundle <400KB gz; Postgres-compatible profile (JSON columns, rules instead of triggers) | UIUX §9, BACKEND_SCHEMA, T8.5 | 6, 8 |

---

## M. MCP servers supporting this build (`mcp_servers.json`)

The MCP config sits next to this file. Selection logic: fill **actual gaps** (live library docs, direct DB
inspection, persistent cross-session memory, GitHub ops) without duplicating tools already native to this
environment (files, shell, git, browser, web search are all covered natively). **Docker is not installed on
this machine** — its MCP entry is ready below but commented out of the active set; add it after installing
Docker Desktop (checklist at the end of this file).

| Server | What it unlocks | Skills served | Status |
|---|---|---|---|
| `context7` | Up-to-date docs for Pydantic v2, SQLAlchemy 2.x, Alembic, FastAPI, PixiJS 8, TanStack Query, Zustand, Tailwind, Recharts — prevents outdated-API hallucination | B6–B16, I55–I59 | active, works today |
| `sqlite` | Direct SQL over `data/agentville.db` to verify ledger conservation (I1/I2), event hash chain (I8), trigger behavior, payment gate (I5) | C19–C27, D34 | active, useful from Phase 0.4 |
| `memory` | Persistent knowledge graph across sessions: locked decisions, invariants, phase state, calibration results | A4, A5 | active, works today |
| `github` | Issues/PRs/CI management for phase gates and experiment reports | A4, K64 | active — **paste your GitHub token into mcp_servers.json first** |
| `docker` (reserved) | Container/sandbox introspection for Phase 3 escape tests and sandbox_runs debugging | G45–G47 | reserved until Docker Desktop installed |

### Docker install checklist (macOS, Apple Silicon) — needed by Phase 3
1. `brew install --cask docker` (or download Docker Desktop for Apple silicon from docker.com).
2. Launch Docker Desktop once; enable "Start when you log in"; default settings are fine.
3. Verify: `docker --version` and `docker run --rm hello-world`.
4. Then add the reserved server to `mcp_servers.json`:
```json
"docker": { "command": "docker", "args": ["run", "-i", "--rm", "alpine/xy:docker-mcp"] }
```
(Use whichever Docker MCP image you prefer at that time; the entry above is a placeholder to remind you where it goes.)
