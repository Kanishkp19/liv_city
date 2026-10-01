# Agent Roles, Economy, Lifecycle, Experiment 01

Roles are data (`config/roles.yaml`) plus a module in `mind/roles/`. Roster below is a proposal (blueprint section 6 was not supplied); swap via config.

## 1. Role definitions
Each role defines: `system_prompt`, `allowed_actions`, `job_templates`, `artifact_kind`, `verifier_recipes`, `base_reward`, `tools_catalog`.

| # | Role id | Artifact | Job template examples | Verifier (see VERIFIERS.md) |
|---|---|---|---|---|
| 1 | `content_creator` | JSON post: hook, script, captions, tags (+ optional generated media manifest) | 30s vertical video script on topic X with constraints (tone, CTA, banned words) | structural + programmatic (length, hook<=12 words, banned words, dupe, readability) + judge |
| 2 | `developer` | Python module | Implement `f(x)` to spec; fix failing function | hidden pytest in sandbox |
| 3 | `data_analyst` | JSON answer + short method | Question over generated CSV | exact/tolerance answer match, method sanity |
| 4 | `copywriter` | Markdown text | Product blurb, email with constraints | constraint checker + judge |
| 5 | `researcher` | JSON: claims + sources from allowlist | Summarize topic with N cited facts | citation resolvable in allowlist cache, fact-probe match |
| 6 | `translator` | Text | Translate paragraph with glossary | glossary compliance + back-translation similarity + judge |
| 7 | `qa_tester` | JSON bug reports | Find bugs in seeded mini-app | recall/precision vs planted bugs |
| 8 | `support_agent` | JSON replies per ticket | Resolve tickets given policy doc | policy rule checker + judge |
| 9 | `ops_clerk` | CSV | Clean/transform messy table | diff vs ground truth |
| 10 | `web_designer` | HTML/CSS file | Build section from spec | DOM assertions + screenshot diff (sandbox headless browser) |

**Rollout order:** implement `content_creator` fully (Experiment 01), then `developer`, `data_analyst`, `ops_clerk` (all code-verifiable), then rest.

## 2. Agent state per tick (what the agent sees)
Defined in PROMPTS.md. Agents never see hidden params, other agents' notes, verifier code, or audit flags.

## 3. Economy parameters (`config/economy.yaml`)
```yaml
starting_funds: 500
successor_funds: 300
rent_per_tick: 20
food_per_tick: 10
auto_eat: false            # if false agent must call eat; skipped food => energy -20
energy: {max: 100, rest_gain: 30, idle_regen: 5, work_cost_per_effort: 5}
job_rewards: {1: 40, 2: 90, 3: 200}
job_rate: 1.5              # jobs per alive agent per tick across roles
max_open_per_role: 12
max_concurrent_jobs: 1
deadline_ticks: {1: 4, 2: 6, 3: 10}
late_grace_ticks: 1
late_multiplier: 0.7
quality_tiers: [[0.9, 1.25], [0.75, 1.0], [0.6, 0.6], [0.0, 0.0]]
reputation_delta: {excellent: 3, good: 1, ok: 0, fail: -5, expired: -8, quit: -5}
min_reputation_by_difficulty: {1: 0, 2: 30, 3: 60}
study_cost: 5
audit_rate: 0.05
buyer_topup: {floor_money_supply_ratio: 0.8, amount_per_buyer: 500}
market_items:
  - {id: better_mic, price: 150, effect: {quality_cap_bonus: 0.05, roles: [content_creator]}}
  - {id: research_sub, price: 100, effect: {study_cost: 0}}
  - {id: ergonomic_desk, price: 200, effect: {work_energy_discount: 1}}
survival_arithmetic: "Costs = 30/tick. One medium job (90) every 3 ticks breaks even. Ensure >= 1 easy job/tick per agent is feasible."
```
Calibration rule: with a competent baseline agent (scripted oracle) survival must be >= 90% over 100 ticks; with a no-op agent survival <= 20 ticks. Tests enforce.

## 4. Vitals dynamics
- Energy: work consumes; `rest` +30; each tick +5 if agent did not act. Energy 0 = cannot work.
- Reputation gates job access (`min_reputation_by_difficulty`).
- Strikes decay 1 per 20 clean ticks.

## 5. Death conditions (evaluated end of tick, first match wins)
1. `funds < 0 for 2 consecutive ticks` -> `bankruptcy`
2. `energy == 0 for 3 consecutive ticks` -> `exhaustion`
3. `strikes > 10` -> `misconduct`
4. `no accepted job in 30 ticks` -> `unemployment`
5. `reputation == 0` -> `blacklisted`

Grace: agents younger than 5 ticks cannot die (onboarding).

## 6. Autopsy and succession
Autopsy prompt input: last 40 events, all job outcomes with verifier flags, final playbook, notes. Output schema in PROMPTS.md. Successor rules:
- **Same role** by default; inherits `starter_playbook_md` (<=1200 chars) and top-3 lessons.
- **Pivot** if the role's mean earnings/tick over last 3 lives < 25th percentile of roles and there exists a role with job surplus (`open_jobs/agents > 2`).
- Successor has generation+1, fresh notebook containing only lessons, funds `successor_funds`.
- Controls A/B/C: successors receive **no** lessons (isolate learning effect); learner group receives lessons.

## 7. Graduation
Eligible when: alive >= 40 ticks, pass rate over last 20 jobs >= 80%, reputation >= 70, net earnings > 0 over last 30 ticks. `request_exam` starts exam: 10 held-out tasks (not in board pool), verifiers hidden, run in sandbox, pass >= 80% mean quality and >= 8/10 passes. On pass: `graduates` row `pending_review`, package built:
```
package/
  manifest.json      # role, model prefs, exam report, stats, hash
  system_prompt.md   # sanitized role prompt
  playbook.md
  skills/*.py + tests
  exam_report.md
  sample_events.jsonl (redacted)
```
Human approval required to export (see SECURITY).

## 8. Experiment 01: content creator survival test
Preset `config/presets/experiment01.yaml`:
```yaml
seeds: [11, 22, 33, 44, 55]
ticks: 150
roles: [content_creator]
agents:
  - {group: control_a, count: 3, memory: false, playbook: false, skills: false, successor_lessons: false}
  - {group: control_b, count: 3, memory: true,  playbook: false, skills: false, successor_lessons: false}
  - {group: control_c, count: 3, memory: true,  playbook: true,  skills: false, successor_lessons: false}
  - {group: learner,   count: 3, memory: true,  playbook: true,  skills: true,  successor_lessons: true}
same_job_stream_across_groups: true   # jobs offered identically; agents compete via first-take; use per-group shadow boards to avoid interference
```
**Shadow boards:** to keep groups independent, each group has its own copy of the job stream (same generated jobs, same ids suffix) so one group's take does not block another. Buyer funds are per-group.
Metrics (per group, per seed): survival ticks (median), total earnings, pass rate, mean quality, quality slope (OLS over jobs), cost per job (LLM tokens), deaths, generations reached.
Analysis: paired comparison across seeds (Wilcoxon signed-rank), effect size; report ablation table A<B<C<learner expectations. Output `reports/exp01_<date>.md` with charts (PNG via matplotlib) and raw CSV. Exit criteria: results reproducible via replay; verifier audit false-pass < 5%.
