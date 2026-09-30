# Config Reference

All config in `config/*.yaml`, validated by pydantic in `config.py`. Env vars override via `AV_` prefix.

## .env.example
```
AV_TOKEN=change-me
AV_DB_URL=sqlite:///data/agentville.db
AV_DATA_DIR=./data
FREELLMAPI_URL=http://localhost:3001/v1
FREELLMAPI_KEY=
OLLAMA_URL=http://localhost:11434
AV_DAILY_TOKEN_CEILING=2000000
AV_SANDBOX_IMAGE_PYTHON=agentville/sandbox-python:latest
AV_LOG_LEVEL=INFO
```

## world preset (`engine/presets/*.yaml`)
```yaml
name: small_city
districts: [housing, office, studio, market, bank, library]
world: {tick_timeout_s: 90, llm_concurrency: 4, snapshot_every: 1}
economy_ref: economy.yaml
agents: [ {role: content_creator, group: learner, count: 3} ]
buyers: {companies: 4, buyers_per_company: 2, initial_budget: 5000}
```

## roles.yaml
```yaml
content_creator:
  title: "Short-form content creator"
  allowed_actions: [take_job, work_on, submit_work, write_note, update_playbook, save_skill, run_skill, study_web, buy_item, rest, eat, request_exam, quit_job, noop]
  artifact_kind: json
  verifier_recipes: {1: content_easy, 2: content_medium, 3: content_hard}
  job_templates: [hook_script, product_teaser, explainer_short]
```

## allowlist.yaml (web study)
```yaml
domains: [wikipedia.org, docs.python.org, developer.mozilla.org, arxiv.org]
max_bytes: 1048576
rate_per_agent_per_tick: 1
```

## judges.yaml
```yaml
panel_size: 3
disagreement_threshold: 0.35
rubrics: {content_hook_v1: judge_rubrics/content_hook_v1.yaml}
```

## Feature flags
`AV_FEATURE_WEB_STUDY`, `AV_FEATURE_EXAMS`, `AV_FEATURE_EXPORT`, `AV_FEATURE_MEDIA_CHECKS` (default off until phases done).

## Makefile targets
`make up|down|test|lint|gate PHASE=n|demo|demo-core|calibrate|frontend|e2e|clean`.
