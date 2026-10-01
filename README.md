# liv_city — AgentVille

A training ground where AI agents must earn a living to stay alive. A simulated city with a real economy: rent, food, job board, buyers, companies, bank. Agents in professional roles take jobs, do the work, and are paid only if independent checkers confirm quality. Agents who cannot earn die and are replaced by better-informed successors. Agents who pass hard exams **graduate** and are exported as tested workers (after your approval).

## What makes it different
1. Money is tied to verified quality, not another AI's opinion.
2. Learning is real but cheap: notebooks, playbooks, skill scripts. No retraining.
3. Nothing reaches the real world without human approval.

## Design principles
1. The game is code; the AI only makes choices. 2. Every action passes a gate. 3. Programs verify first, judges second. 4. Everything is logged and replayable. 5. Provider independence. 6. Turn-based. 7. Fail closed.

## Locked decisions
| Decision | Choice |
|---|---|
| Brain | Free LLM APIs via FreeLLMAPI; local model last-resort |
| First experiment | Content creator survival test, 3 control agents (A/B/C) vs learners |
| Roster | Top 10 roles (AGENT_ROLES_AND_ECONOMY.md) |
| Lifecycle | Vitals, death conditions, autopsy, successor or pivot |
| Sandbox | Docker, no network; read-only web gateway |
| Monitoring | Web Control Room: live map, inspector, replay |

## Architecture
```
Control Room (React) <-WS/REST-> API (FastAPI)
Engine: Clock/Scheduler | World | Ledger | Job board | Lifecycle | Event log
  -> Agent Mind (briefing, memory, playbook, skills)
  -> Action Gateway (permissions, budgets, logging)
  -> Verifier Service (structural, programmatic, judge, audit)
  -> Web Study Gateway (read-only, allowlist, sanitizer)
  -> Export Gate (human approval)
  -> LLM Gateway (queue, limits, fallback, replay) + Docker Sandbox
```

## Documentation map (read in this order if building)
| File | Purpose |
|---|---|
| `AGENTS.md` | Instructions and rules for the coding agent |
| `docs/TRD.md` | Architecture, module contracts, tick algorithm, types |
| `docs/BACKEND_SCHEMA.md` | DDL, triggers, invariants, events |
| `docs/API_SPEC.md` | REST and WebSocket contracts |
| `docs/AGENT_ROLES_AND_ECONOMY.md` | Roles, economy params, lifecycle, Experiment 01 |
| `docs/VERIFIERS.md` | Verification recipes, judges, audits, sandbox contract |
| `docs/PROMPTS.md` | Prompt templates and output schemas |
| `docs/LLM_GATEWAY.md` | Provider routing, limits, replay |
| `docs/SECURITY_AND_SAFETY.md` | Threat model and controls |
| `docs/TESTING.md` | Test strategy and adversarial cases |
| `docs/CONFIG_REFERENCE.md` | YAML, env, Makefile |
| `docs/UIUX_BRIEF.md` | Control Room design spec |
| `docs/IMPLEMENTATION_PLAN.md` | Tasks with acceptance criteria |
| `docs/PRD.md` | Product requirements |
| `docs/DECISIONS.md` | Assumption log |
| `docs/SKILLS.md` | Skill inventory and checklists |
| `docs/TODO.md` | Master subtask roadmap |

## Quickstart (target state)
```bash
cp .env.example .env
docker compose up -d
make demo                # 20-tick smoke with mock LLM + report
python -m agentville.cli new-world --preset experiment01 --seed 11
python -m agentville.cli run --world <id> --ticks 150
open http://localhost:3000
```

## Glossary
**Tick**: one simulation turn. **Vitals**: energy, funds, reputation, strikes. **Playbook**: agent's versioned strategy doc. **Skill**: sandboxed, self-tested script. **Autopsy**: evidence-based post-mortem after death. **Audit plant**: known-good/bad artifact injected to measure verifier accuracy. **Shadow board**: per-group copy of the job stream so groups don't interfere. **Graduate**: agent that passed held-out exams, pending human approval. **Fail closed**: on error the answer is no.

## Status
Planning complete; implementation follows IMPLEMENTATION_PLAN.md.
