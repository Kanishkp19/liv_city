"""LLMGateway: single entry for every model call (LLM_GATEWAY S1, S6-S9)."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydValidationError

from agentville.config import load_providers
from agentville.db.models import LLMCall
from agentville.gateway.llm.base import (
    InvalidModelOutput,
    LLMRequest,
    LLMResponse,
    ProviderUnavailable,
    ReplayMiss,
    redact,
)
from agentville.gateway.llm.providers.mock import MockProvider
from agentville.gateway.llm.ratelimit import RateLimited, TokenBucket


def cache_key(req: LLMRequest) -> str:
    """Provider-agnostic key (system+user+temperature+json_mode+model_hint)."""
    body = json.dumps(
        {"s": req.system, "u": req.user, "t": req.temperature, "j": req.json_mode, "m": req.model_hint},
        sort_keys=True,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class LLMGateway:
    """Routes calls to providers with limits, caching, replay, and full logging."""

    def __init__(self, session: Any, *, providers: list[Any] | None = None, mode: str = "live") -> None:
        self.session = session
        self.mode = mode  # live | replay
        self.buckets: dict[str, TokenBucket] = {}
        self.cache: dict[str, LLMResponse] = {}
        self.call_counts: dict[tuple[str, str, str], int] = {}  # (world,tick,agent)->n
        cfg = load_providers()
        self.providers: dict[str, Any] = {}
        self._remote_cfgs: dict[str, Any] = {}
        for p in cfg.providers:
            if p.kind == "mock" or (providers and p.id in providers):
                self.providers[p.id] = MockProvider(policy="random_valid")
            else:
                self._remote_cfgs[p.id] = p  # built lazily on first use
            self.buckets[p.id] = TokenBucket(rpm=p.rpm, tpm=p.tpm)
        if not self.providers:
            self.providers["mock"] = MockProvider()
            self.buckets["mock"] = TokenBucket(rpm=10_000, tpm=10_000_000)
        self._order = sorted(self.providers)

    async def call(self, req: LLMRequest) -> LLMResponse:
        """Route one request; logs every attempt including failures."""
        k = cache_key(req)
        if req.temperature == 0 and k in self.cache:
            hit = self.cache[k].model_copy(update={"cached": True})
            self._log(req, hit)
            return hit
        if self.mode == "replay":
            resp = self._replay_lookup(req)
            if resp is None:
                raise ReplayMiss(f"no recording for tick={req.tick} agent={req.agent_id} purpose={req.purpose}")
            self._log(req, resp)
            return resp
        errors: list[str] = []
        for pid in self._order:
            bucket = self.buckets[pid]
            if pid in self._remote_cfgs and pid not in self.providers:
                try:
                    self.providers[pid] = _remote_provider(self._remote_cfgs[pid])
                except Exception:  # noqa: BLE001
                    errors.append(f"{pid}: build failed")
                    continue
            try:
                bucket.acquire(est_tokens=(len(req.system) + len(req.user)) // 4 + req.max_tokens // 4)
            except RateLimited as e:
                errors.append(f"{pid}: {e}")
                continue
            started = time.monotonic()
            try:
                resp = await self.providers[pid].complete(req)
                resp.latency_ms = int((time.monotonic() - started) * 1000)
                bucket.record_success()
                if req.temperature == 0:
                    self.cache[k] = resp
                self._log(req, resp, provider=pid, model=resp.model)
                result: LLMResponse = resp
                return result
            except Exception as e:  # noqa: BLE001
                bucket.record_error(not_found="404" in str(e) or "not found" in str(e).lower())
                errors.append(f"{pid}: {e}")
                self._log(req, None, provider=pid, error=str(e))
        raise ProviderUnavailable("; ".join(errors) or "no providers")

    async def call_json(self, req: LLMRequest, schema: type[BaseModel]) -> Any:
        """call + parse + ONE repair retry; returns a validated schema instance (LLM_GATEWAY S7)."""
        resp = await self.call(req)
        parsed = _parse(resp.text, schema)
        if parsed is not None:
            return parsed
        repair_req = req.model_copy(update={
            "system": "Your last reply was not valid JSON for the schema. Reply again with ONLY the JSON object.",
            "user": f"Error: invalid JSON. Original instruction: {req.user[:1000]}",
            "temperature": 0.2,
            "call_index": req.call_index + 1,
        })
        resp2 = await self.call(repair_req)
        parsed = _parse(resp2.text, schema)
        if parsed is None:
            raise InvalidModelOutput("model output unparseable after repair")
        return parsed

    def _replay_lookup(self, req: LLMRequest) -> LLMResponse | None:
        from sqlalchemy import select

        from agentville.db.models import LLMCall as Row

        row = self.session.execute(
            select(Row)
            .where(
                Row.world_id == req.world_id, Row.tick == req.tick,
                Row.agent_id == req.agent_id, Row.purpose == req.purpose,
                Row.call_index == req.call_index, Row.error.is_(None),
            )
            .order_by(Row.id)
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            return None
        return LLMResponse(text=row.response or "", provider=row.provider or "replay", model=row.model or "replay")

    def _log(self, req: LLMRequest, resp: LLMResponse | None, *, provider: str | None = None, model: str | None = None, error: str | None = None) -> None:
        key = (req.world_id, str(req.agent_id), req.purpose)
        n = self.call_counts.get(key, 0)
        self.call_counts[key] = n + 1
        self.session.add(LLMCall(
            world_id=req.world_id, tick=req.tick, agent_id=req.agent_id,
            purpose=req.purpose, call_index=req.call_index or n,
            provider=provider or (resp.provider if resp else None),
            model=model or (resp.model if resp else None),
            prompt_hash=cache_key(req), prompt=redact(req.system + "\n---\n" + req.user),
            response=redact(resp.text) if resp else None,
            tokens_in=resp.tokens_in if resp else None,
            tokens_out=resp.tokens_out if resp else None,
            latency_ms=resp.latency_ms if resp else None,
            cached=bool(resp and resp.cached), repaired=bool(resp and resp.repaired),
            error=error, created_at=_now_iso(),
        ))


def _now_iso() -> str:
    from agentville.clock import Clock

    return Clock().now_iso()


def _parse(text: str, schema: type[BaseModel]) -> BaseModel | None:
    """Strip fences, parse JSON, validate; None on any failure."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw)
        return schema.model_validate(data)
    except (json.JSONDecodeError, PydValidationError, TypeError):
        return None


def _remote_provider(cfg: Any) -> Any:
    """Build an OpenAI-compatible adapter for freellmapi/ollama (httpx, no SDK)."""
    from agentville.gateway.llm.providers.remote import RemoteProvider

    return RemoteProvider(cfg)
