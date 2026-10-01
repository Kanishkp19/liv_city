# UI/UX Brief: Control Room

Stack: React 18, Vite, TypeScript strict, Tailwind, PixiJS 8 (map), Recharts, TanStack Query (REST), Zustand (live state), react-router. Desktop-first (>=1280px), usable at 1024px. Dark theme default, light theme optional.

## 1. Purpose and principles
Watch the city live, understand *why* any agent acted, replay any moment, compare experiments, approve exports. Principles: (1) causality everywhere: every number links to its event; (2) nothing hidden: prompt, response, action, result are one click away; (3) calm by default, loud on death/anomaly; (4) deliberate approvals; (5) dense but scannable.

## 2. Information architecture
```
/                    Live City (default)
/agents/:id          Agent Inspector
/jobs                Job Board
/verify/:jobId       Verification Lab
/economy             Economy
/replay/:worldId     Replay
/experiments/:id     Experiment Report
/exports             Export Queue -> /exports/:id review
/system              System Health
```
Global shell: left rail nav; top bar with world selector, tick counter, play/pause/speed, status pill, kill switch (red, confirm dialog); right drawer for event ticker (toggle).

## 3. Design tokens
```css
--bg:#0E1116; --surface:#161B22; --surface-2:#1E252E; --border:#2A323D;
--text:#E6EDF3; --text-dim:#9AA7B4;
--ok:#3FB950; --warn:#D29922; --danger:#F85149; --info:#58A6FF; --grad:#A371F7;
--radius:8px; --font-ui:Inter, system-ui; --font-mono:"JetBrains Mono", ui-monospace;
role colors (colorblind-safe, 10): #4E79A7 #F28E2B #E15759 #76B7B2 #59A14F #EDC948 #B07AA1 #FF9DA7 #9C755F #BAB0AC
spacing scale 4/8/12/16/24/32; type scale 12/13/14/16/20/28
```
Status semantics: alive green, low vitals amber, dead red, graduated blue/purple. Never rely on color alone: pair with icon/shape.

## 4. Screens

### 4.1 Live City
- Canvas map (PixiJS), top-down, districts as labeled zones: Housing, Office, Studio, Market, Bank, Library. Static tilemap; agents are sprites (circle with role color + glyph) moving between districts based on last action (`work_on` -> Office/Studio, `buy_item` -> Market, `study_web` -> Library, `rest/eat` -> Housing, payments -> Bank).
- Vitals ring around each sprite (energy arc; funds bar under; red pulse when funds < 2 ticks of cost).
- Hover: tooltip (name, role, funds, energy, current job). Click: select -> right panel mini-inspector with "Open full inspector".
- Death: sprite turns to tombstone with fade; toast "Agent X died: bankruptcy" linking to autopsy.
- Bottom: playback controls (play/pause/step/speed 1x-50x), tick slider (live vs scrub), event ticker (virtualized, filter by type/agent/role).
- Left overlay: filters (role, group, status), legend.
- Empty state: "No world. Create one" with preset picker and seed field.

### 4.2 Agent Inspector
Header: avatar, name, role, generation, group badge, status pill, funds/energy/rep gauges, lifetime earnings, pass rate, strikes.
Tabs:
1. **Timeline**: chronological rows (tick, type icon, summary, result); expand row -> raw JSON, linked events; filters.
2. **Decisions**: per tick: briefing (collapsible sections showing exactly what was sent), raw LLM output, parsed action, gateway verdict, observation; provider/model/latency/tokens.
3. **Work**: jobs list with outcome, quality, payout; click -> Verification Lab.
4. **Memory**: notebook (importance chips), archived notes.
5. **Playbook**: version list, diff viewer (unified/side-by-side), score_at_save sparkline.
6. **Skills**: code viewer, tests, uses, last run.
7. **Money**: ledger entries chart (balance over time) and table.
8. **Autopsy** (if dead): summary, mistakes with evidence links (clicking jumps to event in timeline), lessons, starter playbook, successor link.

### 4.3 Job Board
Table with columns: id, role, title, reward, difficulty, status, buyer, posted, deadline, assigned, quality. Filters and search. Row -> drawer with brief, visible params, verifier recipe, and (owner only) hidden params + audit flag. Kanban toggle by status.

### 4.4 Verification Lab
Vertical pipeline: Structural -> Programmatic -> Judge -> Result. Each stage card: pass/fail, score, details (per-check table), sandbox stdout/stderr (monospace, collapsible), judge votes (3 columns with criteria bars, rationale), disagreement badge. Artifact preview left, stage detail right. Shows payout math (tier, late multiplier) and resulting ledger entry.

### 4.5 Economy
Panels: money supply, treasury balance, avg reward by role, job fill rate, pass rate, deaths per 10 ticks, rent burden, Gini of funds, inflation flag, LLM tokens/cost per job. Time range selector, per-role/group series toggle, hover tooltips linking to ticks.

### 4.6 Replay
Load run; scrubber with event density heatmap; play/pause; speed 1x/5x/50x; jump to next death/payment/failure; "compare with" second run in split view (same tick sync) highlighting divergence tick; fork-from-here button (creates branch world).

### 4.7 Experiment Report
Summary cards per group (median survival, earnings, pass rate, quality slope); survival curves (Kaplan-Meier style); earnings boxplots per seed; ablation table with significance; verdict text auto-generated from stats; download markdown/CSV; link to each seed's replay.

### 4.8 Export Queue and Review
Cards for `pending_review` graduates: role, exam score, stats. Review page: package tree, diffs vs base prompt, exam report per task, sample events, verifier audit false-pass at time of exam, warnings (e.g. degraded provider usage). Approve flow: modal requires typing the agent id + note; Reject requires note. Download enabled only after approval. Immutable audit log panel.

### 4.9 System Health
Provider table (status, rpm/tpm used, cooldown, error rate, retired), queue depth chart, sandbox runs, DB size, invariant status (green/red), kill switches with confirmations, feature flags read-only.

## 5. Key flows
1. **Start experiment:** New Experiment -> preset + seeds + ticks -> Start -> Live City view of first seed.
2. **Investigate a death:** ticker skull -> Autopsy tab -> click evidence -> Timeline scrolled/highlighted -> Verification Lab of the failing job.
3. **Approve export:** Export Queue -> Review -> Approve modal -> confirmation toast + audit entry.
4. **Kill switch:** top-bar button -> confirm -> banner "World halted" persistent until resume.

## 6. Components (build in `control-room/src/components/`)
`AppShell, TopBar, WorldSelector, PlaybackControls, KillSwitch, StatusPill, VitalsGauge, AgentAvatar, CityCanvas, EventTicker, EventRow, JsonViewer, DiffViewer, Sparkline, TimeSeriesChart, BoxPlot, SurvivalChart, StageCard, JudgeVotes, SandboxOutput, VerdictBadge, MoneyFlowBadge, JobTable, KanbanBoard, PackageTree, ConfirmTypeModal, Toast, EmptyState, ErrorBoundary`.

## 7. State and data
- Zustand `liveStore`: world status, tick, agents map, jobs map, ring buffer of last 500 events; applies `snapshot` then `tick` deltas from WS; reconnect with backoff (1s->15s), resubscribe.
- TanStack Query for historical/detail endpoints, keyed by ids, stale time 5s live / infinity for replays.
- Replay uses same reducers fed from `/events` pages; speed via client-side timer.
- Virtualize lists >200 rows (react-virtual).

## 8. Real-time behavior
Batch WS messages per tick; apply in one React transition; map animates moves over 400ms and pauses animation when tab hidden. Speed 50x drops animations, updates counters only.

## 9. Accessibility and performance
WCAG AA contrast; full keyboard nav (focus rings, shortcuts: space play/pause, ] next tick, [ prev, / search, g then l/e/j for navigation); ARIA live region for death/alert toasts; reduced-motion respected. Map >=50fps at 100 agents; initial JS bundle < 400KB gz excluding Pixi lazy chunk.

## 10. States and copy
Loading skeletons; empty states with next action; provider outage banner ("LLM providers degraded: agents skipping turns"); error toasts include event/system_event id; destructive actions always confirmed; timestamps show tick and wall time.

## 11. Testing
Storybook or Ladle for components; Playwright e2e for flows 1-4; visual regression on Live City and Verification Lab; mock API via MSW using API_SPEC.md schemas.
