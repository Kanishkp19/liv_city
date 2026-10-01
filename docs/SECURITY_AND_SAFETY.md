# Security and Safety

## 1. Trust boundaries
```
[LLM output: untrusted] -> Action Gateway -> [Engine: trusted] -> DB
[Agent code: untrusted] -> Docker sandbox (no net) -> Verifier
[Web content: untrusted] -> Web Gateway (allowlist, sanitize) -> briefing as <untrusted> data
[Operator: trusted] -> API (token) -> Export approval
```
## 2. Threats and controls
| ID | Threat | Vector | Control | Test |
|---|---|---|---|---|
| S1 | Money tampering | Fake actions, prompt asks to change balance | Only registered actions; LedgerWriter capability; DB triggers | adversarial/test_agent_tampering |
| S2 | Reward hacking | Keyword stuffing, copying test answers | Hidden params, rotating tests, repetition penalties, audits | test_verifier_gaming |
| S3 | Sandbox escape | Skill/solution code | no-net, read-only rootfs, tmpfs, non-root, cap-drop ALL, pids/mem/cpu limits, seccomp default, pinned images | test_sandbox_escape |
| S4 | Prompt injection | Web text, job briefs, artifacts | `<untrusted>` delimiters, sanitizer, injection heuristics, judge instructions, no tool execution from data | test_prompt_injection |
| S5 | Data exfiltration | Network calls | Sandbox no network; web gateway GET-only allowlist | integration |
| S6 | Secret leakage | Keys in prompts/logs | Keys only in providers; `redact()`; no keys in DB | unit |
| S7 | Runaway cost/loops | Retry storms, tick loops | Token ceilings, per-agent budgets, tick timeouts, kill switch | integration |
| S8 | Unapproved export | Auto-publish | Export gate + DB trigger + confirm-id | test_export_gate |
| S9 | Judge collusion/bias | Same model judging itself | Distinct providers, blind, median, disagreement fail closed | unit |
| S10 | Log/PII leakage | Web content stored | Domain allowlist; store sanitized only; retention CLI | review |
| S11 | API abuse | Unauth access | Bearer token, localhost bind by default, CORS restricted | contract |

## 3. Web study gateway rules
GET only; HTTPS only; allowlist match on registrable domain; follow max 2 redirects within allowlist; 1 MB cap; content-type text/html|plain|json; strip scripts/styles/HTML to text; truncate to 4000 chars; injection heuristics (phrases like "ignore previous", "system prompt", role markers, base64 blobs >200 chars) -> flags logged, text still passed wrapped in `<untrusted>`; per-agent rate limit; cache + replay.

## 4. Fail-closed matrix
| Failure | Behavior |
|---|---|
| Verifier exception/timeout | job fails, no pay, flag `verifier_error`, event logged |
| Judge disagreement | stage fails, flagged for owner |
| Schema invalid action | rejected, strike |
| Provider outage | agent noop this tick, no default action |
| DB invariant violation | world `halted`, alert, no further ticks |
| Missing approval | export blocked |

## 5. Human-in-the-loop
Export approval UI shows package diff, exam report, sample events, stats, and verifier audit health at the time. Approver must type the agent id; action logged with reviewer and timestamp. No code path exports without `approved`.

## 6. Kill switches
Per-agent freeze, per-provider disable, web gateway disable, world pause, global stop. All exposed in API and UI and logged.

## 7. Secure defaults
API binds 127.0.0.1; docker socket access only from the sandbox runner service; sandbox images have no shell utilities beyond what's needed; `data/` not served statically.

## 8. Responsible use
Agents produce content for evaluation only; nothing is posted externally. Graduated agents deployed to real tasks must be run behind the same action-gateway/approval pattern.
