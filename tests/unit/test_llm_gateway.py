"""Phase 2 core: gateway call_json/repair, replay, rate limits, briefing gating, redact."""

from __future__ import annotations

import asyncio
import json

import pytest

from agentville.config import load_economy
from agentville.db.models import LLMCall
from agentville.engine.types import AgentState, GroupType, Vitals
from agentville.engine.world import World
from agentville.gateway.llm.base import InvalidModelOutput, LLMRequest, ProviderUnavailable, redact
from agentville.gateway.llm.gateway import LLMGateway, cache_key
from agentville.gateway.llm.providers.mock import MockProvider
from agentville.gateway.llm.ratelimit import RateLimited, TokenBucket
from agentville.mind.briefing import build_briefing


def _req(**kw: object) -> LLMRequest:
    base = dict(world_id="w", tick=1, agent_id="a1", purpose="decide", system="sys", user="usr")
    base.update(kw)
    return LLMRequest(**base)  # type: ignore[arg-type]


def _session():
    from sqlalchemy.orm import Session

    from agentville.db.session import make_engine

    eng = make_engine("sqlite://", apply_triggers=False)
    return eng, Session(eng)


def test_redact_strips_keys() -> None:
    text = "call with sk-abcdef12345678901234 and ghp_" + "x" * 36
    out = redact(text)
    assert "sk-abcdef" not in out and "[REDACTED]" in out


def test_cache_key_provider_agnostic() -> None:
    assert cache_key(_req()) == cache_key(_req())
    assert cache_key(_req()) != cache_key(_req(user="different"))


def test_mock_provider_valid_json() -> None:
    p = MockProvider(policy="random_valid")
    resp = asyncio.run(p.complete(_req()))
    data = json.loads(resp.text)
    assert "action" in data


def test_call_json_repairs_bad_json() -> None:
    from pydantic import BaseModel

    class P(BaseModel):
        action: str
        args: dict = {}  # noqa: ANN001
        reason: str = ""

    eng, s = _session()
    gw = LLMGateway(s, providers=["mock"], mode="live")
    p = MockProvider()
    p.script_reply("decide", "a1", "not json at all", call_index=0)
    p.script_reply("decide", "a1", json.dumps({"action": "noop"}), call_index=1)
    gw.providers["mock"] = p
    out = asyncio.run(gw.call_json(_req(), P))
    assert out.action == "noop"
    repaired_rows = [r for r in s.query(LLMCall).all() if r.call_index and r.call_index > 0]
    assert repaired_rows  # repair attempt logged
    eng.dispose()


def test_call_json_gives_up_after_repair() -> None:
    eng, s = _session()
    gw = LLMGateway(s, providers=["mock"], mode="live")
    p = MockProvider()
    p.script_reply("decide", "a1", "garbage", call_index=0)
    p.script_reply("decide", "a1", "still garbage", call_index=1)
    gw.providers["mock"] = p
    from pydantic import BaseModel

    class P(BaseModel):
        action: str

    with pytest.raises(InvalidModelOutput):
        asyncio.run(gw.call_json(_req(), P))
    eng.dispose()


def test_rate_limiter_rpm_and_cooldown() -> None:
    b = TokenBucket(rpm=2, tpm=100_000)
    b.acquire(10)
    b.acquire(10)
    with pytest.raises(RateLimited):
        b.acquire(10)
    b2 = TokenBucket(rpm=10, tpm=100)
    b2.acquire(90)
    with pytest.raises(RateLimited):
        b2.acquire(90)


def test_circuit_opens_after_3_errors() -> None:
    b = TokenBucket(rpm=100, tpm=100_000)
    b.record_error()
    b.record_error()
    b.acquire(1)  # still open at 2
    b.record_error()
    with pytest.raises(RateLimited):
        b.acquire(1)


def test_retire_after_10_not_found() -> None:
    b = TokenBucket(rpm=100, tpm=100_000)
    for _ in range(10):
        b.record_error(not_found=True)
    assert b.retired
    with pytest.raises(RateLimited):
        b.acquire(1)


def test_all_providers_down_raises_unavailable() -> None:
    eng, s = _session()
    gw = LLMGateway(s, providers=["mock"], mode="live")

    class Boom:
        async def complete(self, req):  # noqa: ANN001, ANN202
            raise RuntimeError("down")

    gw.providers["mock"] = Boom()
    with pytest.raises(ProviderUnavailable):
        asyncio.run(gw.call(_req()))
    rows = s.query(LLMCall).all()
    assert rows and rows[0].error  # failure logged
    eng.dispose()


def _mk_world() -> World:
    w = World(id="w", name="t", seed=1, preset="x", economy=load_economy())
    for g in (GroupType.CONTROL_A, GroupType.LEARNER):
        aid = f"a_{g.value}"
        w.agents[aid] = AgentState(id=aid, world_id="w", role="content_creator", group_type=g,
                                   vitals=Vitals(energy=100, funds=500, reputation=50))
    return w


def test_briefing_group_gating() -> None:
    w = _mk_world()
    a = w.agents["a_control_a"]
    b = build_briefing(w, a, ["obs1"], [{"text": "note"}], "playbook md", ["skill1"])
    assert "NOTEBOOK" not in b.user and "PLAYBOOK" not in b.user
    b2 = build_briefing(w, w.agents["a_learner"], ["obs1"], [{"text": "note"}], "playbook md", ["skill1"])
    assert "NOTEBOOK" in b2.user and "PLAYBOOK" in b2.user


def test_briefing_budget_cap() -> None:
    w = _mk_world()
    a = w.agents["a_learner"]
    huge = "x" * 20_000
    b = build_briefing(w, a, [huge], [{"text": huge}], huge, [huge])
    assert b.approx_tokens <= 6000 + 700  # section budgets sum <= cap with slack


def test_replay_mode_uses_recorded_and_misses_halt() -> None:
    from agentville.gateway.llm.base import ReplayMiss

    eng, s = _session()
    gw = LLMGateway(s, providers=["mock"], mode="replay")
    with pytest.raises(ReplayMiss):
        asyncio.run(gw.call(_req()))
    # record then replay
    s.add(LLMCall(world_id="w", tick=1, agent_id="a1", purpose="decide", call_index=0,
                  provider="mock", model="m", prompt_hash="h", prompt="p", response='{"action":"noop"}',
                  created_at="2026-01-01T00:00:00+00:00"))
    s.flush()
    resp = asyncio.run(gw.call(_req()))
    assert resp.text == '{"action":"noop"}'
    eng.dispose()


# --- live provider wiring (hermetic: fakes, no network) ----------------------

from agentville.config import ProviderCfg, ProvidersCfg  # noqa: E402
from agentville.gateway.llm.providers.remote import EmptyContentError  # noqa: E402


def _live_cfg() -> ProvidersCfg:
    return ProvidersCfg(providers=[
        ProviderCfg(id="r1", kind="freellmapi", model="m1", base_url="http://x/v1",
                    rpm=60, tpm=999999, tier=1),
        ProviderCfg(id="r2", kind="freellmapi", model="m2", base_url="http://x/v1",
                    rpm=60, tpm=999999, tier=2),
    ])


def _fake(behavior: str):  # noqa: ANN202
    from agentville.gateway.llm.base import LLMResponse

    class Fake:
        id = "fake"
        model = "fake-model"

        def __init__(self, behavior: str) -> None:
            self._behavior = behavior

        async def complete(self, req: LLMRequest) -> LLMResponse:
            if self._behavior == "empty":
                raise EmptyContentError("empty content")
            if self._behavior == "boom":
                raise RuntimeError("boom")
            return LLMResponse(text='{"action":"noop"}', provider="fake", model="fake-model")

    return Fake(behavior)


def test_live_providers_route_and_fall_over_empty_content(monkeypatch) -> None:
    eng, s = _session()
    monkeypatch.setattr("agentville.gateway.llm.gateway.load_providers", _live_cfg)
    gw = LLMGateway(s, mode="live")
    assert set(gw.providers) | set(gw._remote_cfgs) >= {"r1", "r2"}
    gw.providers["r1"] = _fake("empty")
    gw.providers["r2"] = _fake("ok")
    resp = asyncio.run(gw.call(_req(temperature=0.7)))
    assert resp.text == '{"action":"noop"}'


def test_all_live_providers_failing_raises_unavailable(monkeypatch) -> None:
    eng, s = _session()
    monkeypatch.setattr("agentville.gateway.llm.gateway.load_providers", _live_cfg)
    gw = LLMGateway(s, mode="live")
    gw.providers["r1"] = _fake("boom")
    gw.providers["r2"] = _fake("boom")
    with pytest.raises(ProviderUnavailable):
        asyncio.run(gw.call(_req(temperature=0.7)))


def _patch_http(monkeypatch, payload: dict, status: int = 200) -> None:  # noqa: ANN001
    from agentville.gateway.llm.providers import remote as rem

    class Resp:
        def __init__(self) -> None:
            self.status_code = status
            self.headers = {}

        def json(self) -> dict:
            return payload

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"http {self.status_code}")

    class Client:
        def __init__(self, **kw: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *a: object) -> bool:
            return False

        async def post(self, url: str, **kw: object) -> Resp:
            Client.last_url = url
            return Resp()

    monkeypatch.setattr(rem.httpx, "AsyncClient", Client)


def test_remote_provider_base_url_precedence(monkeypatch) -> None:
    from agentville.gateway.llm.providers.remote import RemoteProvider

    cfg = ProviderCfg(id="p", kind="freellmapi", model="m", base_url="http://explicit/v1",
                      rpm=10, tpm=10, tier=1)
    monkeypatch.setenv("FREELLMAPI_URL", "http://envhost:9/v1")
    p = RemoteProvider(cfg)
    assert p.base_url == "http://explicit/v1"

    cfg2 = ProviderCfg(id="p2", kind="freellmapi", model="m", rpm=10, tpm=10, tier=1)
    p2 = RemoteProvider(cfg2)
    assert p2.base_url == "http://envhost:9/v1"


def test_remote_provider_empty_content_raises(monkeypatch) -> None:
    from agentville.gateway.llm.providers.remote import RemoteProvider

    cfg = ProviderCfg(id="p", kind="freellmapi", model="m", base_url="http://x/v1",
                      rpm=10, tpm=10, tier=1)
    _patch_http(monkeypatch, {"choices": [{"message": {"role": "assistant", "content": None}}]})
    p = RemoteProvider(cfg)
    with pytest.raises(EmptyContentError):
        asyncio.run(p.complete(_req(temperature=0.7)))


def test_remote_provider_returns_content_and_usage(monkeypatch) -> None:
    from agentville.gateway.llm.providers.remote import RemoteProvider

    cfg = ProviderCfg(id="p", kind="freellmapi", model="m", base_url="http://x/v1",
                      rpm=10, tpm=10, tier=1)
    _patch_http(monkeypatch, {
        "choices": [{"message": {"role": "assistant", "content": '{"action":"work"}'}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    })
    p = RemoteProvider(cfg)
    resp = asyncio.run(p.complete(_req(temperature=0.7)))
    assert resp.text == '{"action":"work"}'
    assert (resp.tokens_in, resp.tokens_out) == (11, 7)
