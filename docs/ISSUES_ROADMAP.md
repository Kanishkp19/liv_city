# GitHub Issues Roadmap (docs/TODO.md Open Tasks)

This catalog details the remaining open tasks from [docs/TODO.md](TODO.md) ready to be opened as GitHub Issues and developed in dedicated feature branches.

---

### T6.22: PixiJS Tilemap Districts Rendering
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `frontend`, `pixijs`
- **Branch**: `feat/T6.22-pixijs-tilemap-districts` (`make branch TASK=6.22`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §4.1
- **Description**: Render grid districts with visual boundary borders, district names, and color accents matching city zones.
- **Verification**: `cd control-room && npm run build`

---

### T6.23: Agent Sprites with Dynamic Vitals Rings
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `frontend`, `pixijs`
- **Branch**: `feat/T6.23-sprites-vitals-rings` (`make branch TASK=6.23`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §4.1
- **Description**: Add visual avatar sprites with radial rings indicating current energy, coin buffer, and strike count badges.
- **Verification**: `cd control-room && npm run test && npm run build`

---

### T6.24: Agent Movement Tween Engine (>=50fps @100 agents)
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `performance`, `pixijs`
- **Branch**: `feat/T6.24-movement-tweens` (`make branch TASK=6.24`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §9
- **Description**: Implement smooth coordinate interpolation between ticks for up to 100 concurrent agents maintaining 50+ FPS.
- **Verification**: `cd control-room && npm run test`

---

### T6.25: Death Tombstone Markers & Event Toasts
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `frontend`, `ui`
- **Branch**: `feat/T6.25-death-tombstone-toasts` (`make branch TASK=6.25`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §4.1
- **Description**: Display tombstone icon when an agent dies (starvation, eviction, bankruptcy) and trigger sliding toast notifications.
- **Verification**: `cd control-room && npm run build`

---

### T6.26: Inspector Timeline Tab with Raw JSON Expansion
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `frontend`, `inspector`
- **Branch**: `feat/T6.26-inspector-timeline-tab` (`make branch TASK=6.26`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §4.2
- **Description**: Add an agent event stream timeline with filtering and accordion expansion to view raw event payloads.
- **Verification**: `cd control-room && npm run build`

---

### T6.27: Inspector Decisions Tab (Briefing + LLM Reasoning + Verdict)
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `frontend`, `llm`
- **Branch**: `feat/T6.27-inspector-decisions-tab` (`make branch TASK=6.27`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §4.2
- **Description**: One-click causality inspection showing the exact briefing prompt sent, the model's raw JSON reasoning, and verifier decision.
- **Verification**: `cd control-room && npm run build`

---

### T6.28: Inspector Work & Money Tabs with Ledger Balance Chart
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `frontend`, `charts`
- **Branch**: `feat/T6.28-work-money-tabs` (`make branch TASK=6.28`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §4.2
- **Description**: Plot an agent's cumulative coin balance, rent debits, and job payouts over time matching ledger balance API.
- **Verification**: `cd control-room && npm run build`

---

### T6.29: Memory, Playbook Diff, and Skills Inspection Tabs
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `frontend`, `diff`
- **Branch**: `feat/T6.29-memory-playbook-skills` (`make branch TASK=6.29`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §4.2
- **Description**: Visual side-by-side diff viewer for agent playbook revisions, notebook notes, and sandboxed skill scripts.
- **Verification**: `cd control-room && npm run build`

---

### T6.30: Job Board, Verification Lab, and Economy Analytics Screens
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `frontend`, `analytics`
- **Branch**: `feat/T6.30-job-board-verification-lab` (`make branch TASK=6.30`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §4.3-4.5
- **Description**: Complete macro dashboards displaying live job streams, verifier judge agreement metrics, and city Gini coefficient.
- **Verification**: `cd control-room && npm run build`

---

### T6.31: Replay Scrubber, Branch Comparison, and ARIA Accessibility
- **Phase**: Phase 6 — API and Control Room
- **Labels**: `enhancement`, `frontend`, `a11y`
- **Branch**: `feat/T6.31-replay-scrubber-a11y` (`make branch TASK=6.31`)
- **Source Doc**: [docs/UIUX_BRIEF.md](UIUX_BRIEF.md) §4.6, §9
- **Description**: Add tick scrubber with forward/rewind, world fork modal, and full keyboard navigation (Space to pause, arrow keys to step).
- **Verification**: `cd control-room && npm run build`

---

### T8.6: Docker Compose Postgres Profile Boot Verification
- **Phase**: Phase 8 — Scale and Hardening
- **Labels**: `enhancement`, `database`, `docker`
- **Branch**: `feat/T8.6-postgres-profile-boot` (`make branch TASK=8.6`)
- **Source Doc**: [docs/BACKEND_SCHEMA.md](BACKEND_SCHEMA.md), [docs/TRD.md](TRD.md)
- **Description**: Test that `docker compose --profile postgres up` brings up Postgres 16, runs Alembic migrations cleanly, and verifies typed JSON columns.
- **Verification**: `docker compose --profile postgres config`

---

### T8.7: LLM Cost Accounting Dashboard & Multi-Run Comparison UI
- **Phase**: Phase 8 — Scale and Hardening
- **Labels**: `enhancement`, `frontend`, `metrics`
- **Branch**: `feat/T8.7-cost-dashboard-comparison` (`make branch TASK=8.7`)
- **Source Doc**: [docs/CONFIG_REFERENCE.md](CONFIG_REFERENCE.md), [docs/UIUX_BRIEF.md](UIUX_BRIEF.md)
- **Description**: Render token usage series categorized by model and provider, and provide split-screen comparison between seeds.
- **Verification**: `uv run pytest tests/unit/test_phase456.py`
