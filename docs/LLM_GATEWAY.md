# LLM Gateway

Single entry for every model call (`gateway/llm/`). Goals: survive free-tier limits and model retirement, log everything, support replay.

## 1. Interface
```python
class LLMRequest(BaseModel):
    world_id:str; tick:int; agent_id:str|None; purpose:Purpose; call_index:int=0
    system:str; user:str; temperature:float; max_tokens:int; json_mode:bool
    priority:int   # 0 highest
    model_hint:str|None  # e.g. agent.model_pref
class LLMResponse(BaseModel):
    text:str; provider:str; model:str; tokens_in:int; tokens_out:int; latency_ms:int; cached:bool; repaired:bool
class LLMGateway:
    async def call(self, req: LLMRequest) -> LLMResponse    # raises ProviderUnavailable
    async def call_json(self, req, schema: type[BaseModel]) -> BaseModel  # parse + 1 repair retry
```

## 2. Provider abstraction
`providers/base.py::Provider` with `async complete(req) -> RawResponse`, `capabilities` (json_mode, max_context, streaming). Implementations: `freellmapi` (OpenAI-compatible HTTP to `FREELLMAPI_URL`, model chosen by router), `ollama` (local), `mock`. `config/providers.yaml`:
```yaml
providers:
  - {id: freellm_a, kind: freellmapi, model: "<model-id-1>", rpm: 15, tpm: 200000, tier: 1, judge_ok: true}
  - {id: freellm_b, kind: freellmapi, model: "<model-id-2>", rpm: 10, tpm: 150000, tier: 1, judge_ok: true}
  - {id: freellm_c, kind: freellmapi, model: "<model-id-3>", rpm: 10, tpm: 100000, tier: 2, judge_ok: true}
  - {id: local, kind: ollama, model: "llama3.1:8b", rpm: 60, tpm: 999999, tier: 9, judge_ok: false}
router: {strategy: weighted_health, fallback_order: [tier1, tier2, local], judge_distinct_providers: true}
```

## 3. Queue and scheduling
`asyncio.PriorityQueue` keyed `(priority, enqueue_seq)`. Priorities: 0 judge/verification, 1 agent decide, 2 produce_artifact, 3 autopsy, 4 summarize. Worker pool size = `min(sum(provider concurrency), 4)`. Each worker: pick request -> router selects provider with token budget available -> rate limiter `acquire(provider, est_tokens)` -> call with timeout (30s) -> log.

## 4. Rate limiting
Token-bucket per provider for RPM and TPM (sliding 60s window). On HTTP 429 read `Retry-After`, set `cooldown_until`. After 3 consecutive errors: circuit open for 60s (exponential to 15 min). Provider marked `retired` after 10 consecutive 404/model-not-found; alert in Control Room.

## 5. Routing rules
1. Respect `model_hint` if provider healthy.
2. Judge calls: choose distinct providers per panel member (`judge_distinct_providers`).
3. Otherwise weighted by remaining capacity and recent latency.
4. Fallback chain on failure: next healthy provider; local model last resort (flag `degraded=true` in event; degraded calls excluded from Experiment 01 metrics unless configured).
5. If all fail: `ProviderUnavailable`; engine skips agent (noop).

## 6. Caching
Key = sha256(provider-agnostic: system+user+temperature+json_mode+model_hint). Cache used only when `temperature==0` (judges, autopsy) or in replay mode. Stored in `llm_calls` (cached=1 rows reference original).

## 7. Structured output
`call_json`: (1) request with `json_mode` if supported else instruct; (2) strip code fences; (3) `json.loads`; (4) pydantic validate; (5) on failure send repair prompt once (marked `repaired=1`); (6) still invalid -> raise `InvalidModelOutput` -> action gateway treats as invalid proposal (strike only if not provider-flaky, i.e. response was non-empty).

## 8. Logging and replay
Every attempt inserts `llm_calls` row (including failed ones with error). Replay mode: `ReplayProvider` looks up `(source_world_id, tick, agent_id, purpose, call_index)`; missing record raises `ReplayMiss` and halts (no silent live call).

## 9. Cost/token accounting
Track tokens per agent, purpose, and world; expose in `/economy` and reports ("cost per job"). Budget guard: per-world daily token ceiling (config); when reached, world pauses with alert.

## 10. Security
API keys read from env only inside providers; prompts pass through `redact()` that strips strings matching key patterns; response text never executed.

## 11. Tests
Provider failover simulation, 429 handling, JSON repair paths, replay determinism, priority ordering under load, judge distinctness.
