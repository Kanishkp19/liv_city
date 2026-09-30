# API Spec

Base: `http://localhost:8000/api/v1`. JSON. Auth: single-owner bearer token (`Authorization: Bearer $AV_TOKEN`) for v1; WS uses `?token=`. Errors: `{ "error": {"code": "not_found", "message": "...", "details": {}} }` with proper HTTP status. Pagination: `?limit=50&cursor=<opaque>` -> `{ "items": [...], "next_cursor": "..."|null }`.

## Worlds
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/worlds` | `{name, preset, seed, overrides?}` | `World` |
| GET | `/worlds` | | list |
| GET | `/worlds/{id}` | | `World` + counts |
| POST | `/worlds/{id}/run` | `{ticks:int, speed?:"max"|"paced", pace_ms?:int}` | `{run_id}` (async) |
| POST | `/worlds/{id}/pause` `/resume` `/stop` | | `World` |
| GET | `/worlds/{id}/state?tick=` | | Snapshot (agents, jobs open, economy) |
| POST | `/worlds/{id}/fork` | `{from_tick}` | new `World` (branch) |
| POST | `/worlds/{id}/replay` | `{until_tick?}` | new `World` in replay mode |

## Agents
| GET | `/worlds/{w}/agents?status=&role=&group=` | list summaries |
| GET | `/agents/{id}` | full state: vitals, job, inventory, playbook, counts |
| GET | `/agents/{id}/timeline?from=&to=&types=` | events + actions merged |
| GET | `/agents/{id}/llm-calls?tick=` | prompts/responses |
| GET | `/agents/{id}/notes` `/playbooks` `/skills` | |
| GET | `/agents/{id}/autopsy` | |
| POST | `/agents/{id}/freeze` `/unfreeze` | kill switch |

## Jobs and verification
| GET | `/worlds/{w}/jobs?status=&role=` | |
| GET | `/jobs/{id}` | job (hidden params only if `?owner=1`) |
| GET | `/jobs/{id}/verifications` | stages, judge votes, sandbox output |
| GET | `/artifacts/{id}/content` | raw/preview |

## Economy and analytics
| GET | `/worlds/{w}/economy?from=&to=` | series: money_supply, avg_reward, fill_rate, pass_rate, deaths, gini |
| GET | `/worlds/{w}/leaderboard?by=earnings|survival|pass_rate` | |
| GET | `/worlds/{w}/ledger?account=` | entries |
| GET | `/experiments/{id}/report` | JSON + `report_path` markdown |
| POST | `/experiments` | `{preset, seeds:[...], ticks}` -> runs N worlds |

## Exports (human gate)
| GET | `/graduates?status=` | |
| GET | `/graduates/{id}` | package manifest, exam report, diff |
| POST | `/graduates/{id}/approve` | `{reviewer, note, confirm_agent_id}` -> requires `confirm_agent_id == agent id` |
| POST | `/graduates/{id}/reject` | `{reviewer, note}` |
| GET | `/graduates/{id}/download` | zip; only when `approved` |

## System
| GET | `/system/health` | providers, queue depth, sandbox, db |
| GET | `/system/providers` `POST /system/providers/{p}/disable` | |
| POST | `/system/kill` | global stop |
| GET | `/metrics` | Prometheus |

## WebSocket `/ws?world_id=&token=`
Server -> client messages: `{"t":"tick","world_id","tick","events":[...],"deltas":{agents:[...],jobs:[...],economy:{...}},"event_hash"}`, `{"t":"alert","level","message"}`, `{"t":"status","status"}`. Client -> server: `{"t":"subscribe","agent_id"}` for detailed streams; `{"t":"speed","value":1|5|50}` (replay). On connect server sends `{"t":"snapshot",...}`.

## Pydantic response models (must exist in `api/schemas.py`)
`WorldOut, AgentSummary, AgentDetail, JobOut, VerificationOut, EventOut, EconomyPoint, GraduateOut, ExperimentReport, ProviderStatus, TickMessage`.
