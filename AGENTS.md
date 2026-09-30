# AGENTS.md: Instructions for the Coding Agent

You are building **AgentVille** end to end. Read this file first, then the docs in the order below. Do not ask for clarification on anything these docs define; make the smallest reasonable assumption, record it in `docs/DECISIONS.md`, and continue.

## Read order
1. `README.md` (overview, layout)
2. `docs/TRD.md` (architecture, module contracts, tick algorithm)
3. `docs/BACKEND_SCHEMA.md` (tables, triggers, invariants)
4. `docs/API_SPEC.md` (REST/WS contracts)
5. `docs/AGENT_ROLES_AND_ECONOMY.md` (roles, economy, lifecycle, Experiment 01)
6. `docs/VERIFIERS.md` (verification recipes)
7. `docs/PROMPTS.md` (briefing + output schemas)
8. `docs/LLM_GATEWAY.md`
9. `docs/SECURITY_AND_SAFETY.md`
10. `docs/TESTING.md`, `docs/CONFIG_REFERENCE.md`
11. `docs/UIUX_BRIEF.md` (only when reaching the Control Room phase)
12. `docs/IMPLEMENTATION_PLAN.md` (the order of work; each task has acceptance criteria)

## Non-negotiable rules
1. **Engine is ordinary code.** LLMs only choose actions. No LLM output may write to the DB, ledger, or filesystem outside the action gateway.
2. **Money is integer coins.** No floats for money anywhere. Ledger is append-only and double-entry.
3. **Fail closed.** Any verifier/gateway/provider error yields rejection or no-op, never a default success.
4. **Determinism.** All randomness comes from `world.rng(tick, purpose)`. No `random`, `time.time()`, `uuid4()` in engine logic; use injected `Clock` and `IdGen`.
5. **Everything logged.** Every state change emits an event; every LLM call is stored with prompt and response.
6. **No network in sandbox.** No agent-controlled code runs outside Docker.
7. **Nothing leaves the system without a human approval record.**
8. **Provider-agnostic.** Never import a provider SDK outside `gateway/llm/providers/`.

## Tech constraints
Python 3.12, FastAPI, SQLAlchemy 2.x (typed), Alembic, Pydantic v2, pytest, hypothesis, httpx, docker SDK. Frontend: React 18, Vite, TypeScript strict, PixiJS 8, Recharts, TanStack Query, Zustand, Tailwind. Lint: ruff + mypy --strict (engine, gateway, verifier). ESLint + tsc for frontend.

## Working method
- Implement tasks in `IMPLEMENTATION_PLAN.md` order. One task = one commit. Commit message: `T<id>: <title>`.
- Before coding a task: write its tests from the acceptance criteria. Then implement until green.
- After each phase run `make gate PHASE=<n>`; do not begin the next phase on red.
- Keep functions small and pure where possible; side effects live at the edges (gateway, db, sandbox).
- Every public function has type hints and a one-line docstring.
- When docs conflict: schema doc wins for data, TRD wins for behavior, API_SPEC wins for wire formats.

## Definition of done (per task)
Tests written and passing; mypy/ruff clean; events emitted and documented in `BACKEND_SCHEMA.md` event list; fail-closed path tested; no TODOs without an entry in `docs/DECISIONS.md`.

## Deliverables checklist
- [ ] `docker compose up` brings up db, engine api, control room, sandbox image builds
- [ ] `make demo` runs Experiment 01 smoke (20 ticks, mock LLM) and prints a report
- [ ] `make test`, `make lint`, `make gate` all pass
- [ ] Replay of any run reproduces identical event hash
