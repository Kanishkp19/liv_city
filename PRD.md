# PRD: AgentVille

Version 2.0 | Owner: Kanishk | Status: Ready for build

## 1. Problem
Agent demos are judged by vibes: one LLM grades another, "learning" is prompt tweaking, and there is no cheap way to discover which agent setups do real work reliably. Free LLM APIs are rate-limited and unstable, so real-time multi-agent sims are impractical.

## 2. Vision
An economic selection environment where survival requires **verified** output quality. Surviving agents (prompt + playbook + skill scripts + notes) become tested, exportable workers. Learning is real but cheap: no retraining.

## 3. Users and jobs to be done
| User | JTBD |
|---|---|
| Owner/operator | Run experiments, watch agents, understand why they live/die, export proven workers safely |
| Researcher | Compare memory/playbook/skill ablations across seeds with reproducible replays |
| Future collaborator | Add roles, jobs, verifiers without touching the engine core |

## 4. Goals / Non-goals
**Goals:** money tied to verified quality; determinism and replay; provider independence; free-tier feasibility; human approval before export; explainability of every decision.
**Non-goals (v1):** real-time simulation, fine-tuning, real money, multi-tenant SaaS, autonomous real-world actions, unrestricted browsing, agent-to-agent negotiation (v2).

## 5. Core concepts (glossary)
World, Tick, Agent, Role, Job, Buyer, Verifier, Ledger, Vitals, Playbook, Skill, Autopsy, Successor, Pivot, Graduate, Exam, Audit plant, Shadow board, Control group. Definitions in `GLOSSARY` section of README.

## 6. User stories with acceptance criteria
| ID | Story | AC |
|---|---|---|
| US1 | As owner I create a world from a preset and seed | POST /worlds returns world; same seed twice yields identical initial state |
| US2 | I run N ticks and watch live | WS streams events each tick; UI updates within 500ms of commit |
| US3 | I click an agent and see why it acted | Inspector shows briefing, raw LLM response, parsed action, result, events |
| US4 | I see money only moves on verified work | Every payment links to verification rows; no path otherwise |
| US5 | I see an agent die and read its autopsy | Death event, cause, autopsy with evidence-linked lessons, successor |
| US6 | I replay any run and get identical results | Replay hash equals original |
| US7 | I run Experiment 01 and get a report | 5 seeds, 4 groups, stats and charts produced |
| US8 | I review and approve a graduate export | Approval requires typing agent id; logged; download unlocked only after |
| US9 | I stop everything instantly | Kill switch halts within 1 tick and blocks provider calls |
| US10 | I add a new role via config + module | Documented steps; passes verifier gold tests |

## 7. Functional requirements
| ID | Requirement | Pri | Phase |
|---|---|---|---|
| F1 | Seeded deterministic turn-based engine | P0 | 1 |
| F2 | Append-only double-entry ledger, engine-only writes | P0 | 0 |
| F3 | Job board, generator, buyers, companies | P0 | 1 |
| F4 | Action gateway (schema, permission, budget, idempotency) | P0 | 1 |
| F5 | Vitals, costs, death conditions | P0 | 1 |
| F6 | LLM Gateway (queue, limits, fallback, log, replay) | P0 | 2 |
| F7 | Briefing builder with token budgets | P0 | 2 |
| F8 | Verifier service: structural, programmatic, judge, audit | P0 | 3 |
| F9 | Docker sandbox | P0 | 3 |
| F10 | Payment only on verified pass | P0 | 3 |
| F11 | Notebook, playbook, skills | P1 | 2/4 |
| F12 | Autopsy, successor, pivot | P0 | 4 |
| F13 | Experiment 01 runner and report | P0 | 5 |
| F14 | REST API + WebSocket | P0 | 6 |
| F15 | Control Room (map, inspector, economy, replay) | P1 | 6 |
| F16 | Web study gateway | P1 | 7 |
| F17 | Exams, graduation, export gate | P1 | 7 |
| F18 | Additional roles | P2 | 8 |
| F19 | Run forking (branch from tick) | P2 | 8 |

## 8. Non-functional requirements
Determinism 100% under replay; ledger integrity 100%; engine overhead <200ms/tick excluding LLM; WS payload <100KB/tick; cost $0 on free tiers; recoverability from crash via snapshots; all secrets in env; accessibility AA in UI.

## 9. Success metrics
| Metric | Target |
|---|---|
| Replay determinism | 100% |
| Verifier audit false-pass | <5% |
| Oracle agent survival | >=90% at 100 ticks |
| Exp01 learners vs control A survival/earnings | Positive effect, reported with paired stats over 5 seeds |
| Graduated agent pass rate on held-out real tasks | >=70% |
| Time to first watchable run from clone | <15 min |

## 10. Experiment 01 (first milestone)
See AGENT_ROLES_AND_ECONOMY.md section 8. Hypothesis: A < B < C < Learner on survival and earnings; effect visible by tick 100.

## 11. Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Free API limits/retirement | High | High | Multi-provider router, cache, local fallback, turn-based |
| Reward hacking | Med | High | Hidden tests, audits, programs over judges |
| Judge bias/injection | Med | Med | Panel, blind, disagreement fail closed, delimiters |
| Economy imbalance | High | Med | Calibration suite, tunable YAML |
| Scope creep | High | Med | Phase gates, P2 backlog |
| Sandbox escape | Low | High | Defense in depth, adversarial tests |

## 12. Dependencies
FreeLLMAPI endpoint, Docker, Python 3.12, Node 20, ffmpeg (media checks, optional).

## 13. Open questions (tracked in DECISIONS.md)
Final roster; graduation thresholds; long-run judge cost; whether to add agent-to-agent trade in v2.
