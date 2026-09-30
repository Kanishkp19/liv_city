# TRD: AgentVille Technical Requirements and Design

Audience: coding agent. Everything here is normative unless marked *(guidance)*.

## 1. Repository layout (authoritative)
```
agentville/
  pyproject.toml  Makefile  docker-compose.yml  .env.example  alembic.ini
  src/agentville/
    __init__.py
    config.py                 # pydantic-settings, loads config/*.yaml
    ids.py                    # IdGen (deterministic, seeded)
    clock.py                  # Clock (tick counter; wall-clock only for created_at)
    rng.py                    # DeterministicRNG: rng(world_seed, tick, purpose, agent_id?)
    db/
      base.py models.py session.py migrations/ triggers.sql
    engine/
      world.py                # World aggregate + snapshot/restore
      scheduler.py            # Tick loop (section 4)
      ledger.py               # Ledger: post(), balance(), reconcile()
      events.py               # EventLog.emit(), hashing, EventType enum
      jobs.py                 # JobGenerator, JobBoard state machine
      market.py               # buyers, companies, price/reward model
      lifecycle.py            # vitals, costs, death, autopsy trigger, succession
      exams.py                # exam runner, graduation
      presets/                # experiment01.yaml, small_city.yaml
    mind/
      briefing.py             # build_briefing(agent, world_view) -> Briefing
      memory.py               # notebook ops, summarization
      playbook.py             # versioned playbook
      skills.py               # skill save/run (sandboxed)
      roles/                  # one module per role: prompt, tools, job templates
    gateway/
      actions/
        registry.py           # ActionSpec registry
        validator.py          # schema + permission + budget + idempotency
        handlers/*.py         # one handler per action
      llm/
        gateway.py queue.py router.py ratelimit.py cache.py replay.py
        providers/{freellmapi.py, ollama.py, mock.py}
      web/
        fetcher.py sanitizer.py allowlist.py
    verifier/
      service.py              # VerifierService.verify(job, artifact) -> VerificationResult
      recipes/                # structural.py programmatic_*.py judge.py audit.py
      judge_rubrics/*.yaml
    sandbox/
      runner.py images/{python,node,media}/Dockerfile
    export/
      packager.py approval.py
    api/
      main.py deps.py routes/{worlds,agents,jobs,economy,replay,exports,system}.py ws.py
    cli/main.py               # typer: new-world, run, inspect, replay, report, export
    reports/experiment.py
  control-room/               # React app (see UIUX_BRIEF.md)
  config/{providers.yaml, economy.yaml, roles.yaml, allowlist.yaml, judges.yaml}
  tests/{unit,property,golden,integration,adversarial}/
  docs/
```

## 2. Core domain types (Pydantic v2, in `src/agentville/engine/types.py`)
```python
Coins = int  # never float

class AgentStatus(StrEnum): ALIVE="alive"; DEAD="dead"; GRADUATED="graduated"; PIVOTED="pivoted"
class JobStatus(StrEnum): OPEN="open"; TAKEN="taken"; SUBMITTED="submitted"; PASS="verified_pass"; FAIL="verified_fail"; EXPIRED="expired"

class Vitals(BaseModel):
    energy: int = Field(ge=0, le=100)
    funds: Coins
    reputation: float = Field(ge=0, le=100)
    strikes: int = 0

class AgentState(BaseModel):
    id: str; world_id: str; role: str; generation: int; parent_id: str | None
    group_type: Literal["learner","control_a","control_b","control_c"]
    status: AgentStatus; vitals: Vitals; location: str
    born_tick: int; current_job_id: str | None
    inventory: dict[str, int] = {}   # purchased tools -> level
    idle_ticks: int = 0; low_energy_ticks: int = 0; negative_funds_ticks: int = 0

class JobSpec(BaseModel):
    id: str; role: str; title: str; buyer_id: str
    brief: str                     # human-readable request shown to agent
    params: dict[str, Any]         # machine params used by verifier (may include hidden fields)
    visible_params: dict[str, Any] # subset shown to agent
    reward: Coins; penalty: Coins = 0; difficulty: Literal[1,2,3]
    posted_tick: int; deadline_tick: int
    verifier_recipe: VerifierRecipe
    is_audit_plant: bool = False

class Proposal(BaseModel):         # what the LLM returns
    action: str; args: dict[str, Any] = {}; reason: str = Field(max_length=400)

class ActionResult(BaseModel):
    status: Literal["accepted","rejected","error"]
    reject_reason: str | None = None
    energy_cost: int = 0; coin_delta: Coins = 0
    observation: str                # text fed back into next briefing
```

## 3. Module contracts
### 3.1 Ledger (`engine/ledger.py`)
```python
class Ledger:
    def post(self, *, tick:int, debit:str, credit:str, amount:Coins, reason:str,
             ref_type:str|None=None, ref_id:str|None=None, event_id:int|None=None) -> int
        # raises LedgerError if amount<=0, or debit is an agent account and would go negative
    def balance(self, account:str) -> Coins
    def reconcile(self, world_id:str) -> None  # raises if SUM(debit)!=SUM(credit) by construction check
```
Accounts: `agent:<id>`, `bank`, `treasury`, `buyer:<id>`, `landlord`, `market`. Convention: `debit` = account money leaves, `credit` = account money arrives. Balance = credits - debits. Treasury seeded at world creation.
Only `engine/*` and gateway handlers may call `post`. Enforce by a `LedgerWriter` capability object passed in, not importable globally.

### 3.2 EventLog
`emit(world_id, tick, type, agent_id, payload, cause_event_id=None) -> event_id`. Each event gets `seq` (per tick, monotonically increasing) and contributes to a rolling `event_hash = sha256(prev_hash + canonical_json(event))` stored in `snapshots`. Replay equality = equal final hash.

### 3.3 JobGenerator
`generate(world, tick) -> list[JobSpec]`. Uses `rng(seed,tick,"jobs")`. Count per role = Poisson(lambda = economy.job_rate * alive_agents_in_role) capped at `economy.max_open_per_role`. Difficulty mix 50/35/15 (easy/medium/hard). Template registry per role (see `mind/roles/<role>.py::JobTemplate.make(rng, difficulty) -> JobSpec`). `is_audit_plant` set with prob `economy.audit_rate` (default 0.05); plants embed a known-bad artifact expectation (see VERIFIERS.md section 7).

### 3.4 JobBoard state machine
```
OPEN --take_job--> TAKEN --submit_work--> SUBMITTED --verify_pass--> VERIFIED_PASS
  |                  |                       \--verify_fail--> VERIFIED_FAIL
  \--deadline--> EXPIRED   TAKEN --deadline--> EXPIRED (penalty applied)
```
One agent per job. An agent holds at most `economy.max_concurrent_jobs` (default 1). Submitting after deadline allowed only until `deadline+grace` (default 1 tick) with late multiplier.

### 3.5 Lifecycle
`apply_costs(world, tick)`: for each alive agent: rent (post agent->landlord), food (agent->market) if agent chose `eat`/auto-eat rule (see economy). If funds < cost: pay what's possible, set `negative_funds_ticks += 1`, apply energy penalty.
`check_deaths(world, tick) -> list[Death]`: conditions in AGENT_ROLES_AND_ECONOMY.md section 5. On death: emit `agent_died`, status=dead, freeze jobs (release assigned job to OPEN, penalty none), enqueue autopsy.
`spawn_successor(dead_agent, autopsy) -> AgentState`: same role unless pivot rule; funds = `economy.successor_funds`; inherits autopsy lessons + best playbook of the dead agent by score (curated, never raw notes).

### 3.6 Action gateway pipeline
```
raw LLM text -> parse JSON (1 repair retry via LLM Gateway) -> Proposal
 -> validator: (1) action exists (2) role permission (3) args pydantic schema for that action
               (4) preconditions (energy, funds, job state, location) (5) rate limits (per tick 1 action, per-agent budget)
               (6) idempotency key = sha256(agent, tick, action, args)
 -> handler.execute(ctx) -> ActionResult
 -> record in `actions`; emit events; append observation to agent's next briefing
```
Rejected proposals: `strikes += 1` only for invalid schema/unknown action/permission violations (not for legitimately failed attempts like insufficient energy).

### 3.7 Action registry (all v1 actions)
| Action | Args | Energy | Effects |
|---|---|---|---|
| `take_job` | job_id | 2 | Assign job if OPEN, role match, reputation >= min_rep |
| `work_on` | job_id, effort: 1-3, approach: str<=300 | 5*effort | Adds progress; generates draft via `produce_artifact` LLM call in role module (see PROMPTS.md) |
| `submit_work` | job_id, artifact_id | 1 | Moves job to SUBMITTED, queues verification |
| `write_note` | text<=280, importance 1-5 | 0 | Adds notebook entry (cap 50) |
| `update_playbook` | body_md<=2000 chars | 1 | New version; requires evidence: last 3 job outcomes referenced |
| `save_skill` | name, code, tests | 3 | Runs tests in sandbox; saved only if all pass |
| `run_skill` | name, input | 2 | Runs in sandbox, returns output as observation |
| `study_web` | url or query | 1 + 5 coins | Via web gateway; returns sanitized text (<=4000 chars) |
| `buy_item` | item_id | 0 | Purchase from market catalog; raises quality cap or lowers costs |
| `rest` | none | -30 (restores) | |
| `eat` | none | 0 | Pay food cost; prevents starvation penalty |
| `request_exam` | exam_id | 10 | Only if graduation criteria met (see lifecycle) |
| `quit_job` | job_id | 0 | Releases job; -5 reputation |
| `noop` | none | 0 | Explicit skip |

Each action handler: `class Handler(Protocol): spec: ActionSpec; def validate(self, ctx, args) -> None; def execute(self, ctx, args) -> ActionResult`.

## 4. Tick algorithm (authoritative)
```
def run_tick(world):
    t = world.tick + 1
    with db.transaction() as tx:
        emit(tick_started)
        expire_jobs(t)                                   # OPEN/TAKEN past deadline
        new_jobs = JobGenerator.generate(world, t); post(new_jobs)
        order = rng(seed,t,"order").shuffle(alive_agents)
        proposals = await gather_bounded(                # concurrency limited by LLM Gateway
            {a.id: mind.decide(a, world_view(a,t)) for a in order}, timeout=cfg.tick_timeout)
        for a in order:                                  # apply sequentially in seeded order
            result = gateway.execute(a, proposals[a.id])
        await VerifierService.run_pending(t)             # submissions from this and prior ticks
        settle_payments(t)                               # only verified_pass -> ledger
        lifecycle.apply_costs(t)
        deaths = lifecycle.check_deaths(t); for d in deaths: autopsy+successor (LLM, low priority; may complete t+1)
        market.update_prices(t)
        ledger.reconcile()
        snapshot(t); emit(tick_committed, event_hash)
    world.tick = t
```
Timeout handling: if an agent's decision exceeds timeout or provider is down, that agent's action is `noop` and event `agent_decision_skipped` is emitted (no strike). Whole-tick failure rolls back the transaction; world tick unchanged; error event stored separately (non-transactional table `system_events`).

### Concurrency model
LLM decisions run concurrently (bounded by gateway concurrency, default 4); state mutation is single-threaded and sequential in seeded order. Verification jobs run concurrently but settle in job-id order.

## 5. Determinism and replay
- `rng(seed,tick,purpose,agent_id=None)` = `random.Random(sha256(f"{seed}:{tick}:{purpose}:{agent_id}"))`.
- IDs: `IdGen.next(kind)` counter-based per world (`agent_0007`, `job_000123`).
- Replay mode: LLM Gateway serves recorded responses keyed by `(world_id, tick, agent_id, purpose, call_index)`. Sandbox outputs are also recorded (`sandbox_runs`) and replayed. Web fetches replayed from `web_fetches` cache.
- Golden test: run 100 ticks with mock provider, save event_hash; second run with replay must match.

## 6. Verification service interface
```python
class VerificationResult(BaseModel):
    passed: bool; quality: float  # 0..1
    stages: list[StageResult]; flags: list[str]
class VerifierService:
    async def verify(self, job: JobSpec, artifact: Artifact) -> VerificationResult
```
Stage order fixed: structural -> programmatic -> judge (if recipe requires) -> (audit bookkeeping). Any stage error => `passed=False, flags=["verifier_error"]`. Full recipes in `VERIFIERS.md`.

## 7. Payment computation
```
base = job.reward
tier_mult = {q>=0.9:1.25, q>=0.75:1.0, q>=0.6:0.6, else:0}[quality]
late_mult = 0.7 if submitted after deadline else 1.0
payout = floor(base * tier_mult * late_mult)
ledger.post(debit=f"buyer:{buyer}", credit=f"agent:{agent}", amount=payout, reason="job_payment")
reputation += {q>=0.9:+3, q>=0.75:+1, q>=0.6:0, else:-5}
```
Buyer accounts are funded from treasury at world start and topped up by market rule; if buyer lacks funds, job is not posted.

## 8. Memory system
- **Notebook**: <=50 notes. On overflow, LLM `summarize_notes` (low priority) merges lowest-importance 10 into 2.
- **Playbook**: markdown, <=2000 chars, versioned; `score_at_save` = trailing 10-job pass rate.
- **Skills**: python (or js) functions with tests; execute only in sandbox; exposed to agent as `run_skill(name, input)`.
- **Briefing budget**: hard cap 6,000 tokens: system(role) 600, vitals+world 300, open jobs (top 8) 900, active job 500, recent observations (5) 800, notebook (top 12 by importance/recency) 700, playbook 500, skills index 200, buffer for output. Controls in group A/B/C zero out sections (see experiment config).

## 9. Error taxonomy
`ValidationError` (agent fault, strike) / `PreconditionFailed` (no strike) / `ProviderUnavailable` (skip) / `VerifierError` (fail closed) / `SandboxTimeout` (verifier fail, or skill fail) / `LedgerError` (fatal for tick, rollback) / `InvariantViolation` (halt world, alert).

## 10. Observability
Structured logs (JSON) with `world_id, tick, agent_id, event_id`. Metrics endpoint `/metrics` (Prometheus text): `tick_duration_seconds`, `llm_queue_depth`, `llm_call_latency`, `provider_errors_total`, `verifier_pass_ratio`, `agents_alive`, `money_supply`. 

## 11. Performance targets
100 agents x 1 decision/tick; tick wall time bounded by LLM throughput, not engine (engine overhead < 200 ms/tick excluding LLM). SQLite WAL, batch inserts per tick. Control Room WS payload per tick < 100 KB (delta-encoded).
