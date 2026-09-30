"""Mock provider: deterministic scripted responses for tests and offline runs."""

from __future__ import annotations

import json

from agentville.gateway.llm.base import LLMRequest, LLMResponse
from agentville.rng import derive_rng


class MockProvider:
    """Returns valid action JSON per policy; ignores network entirely."""

    id = "mock"
    model = "mock-1"

    def __init__(self, policy: str = "random_valid") -> None:
        self.policy = policy
        self.script: dict[tuple[str, str], str] = {}  # (purpose, agent_id) -> canned text
        self.script_by_call: dict[tuple[str, str, int], str] = {}  # exact call_index wins

    def script_reply(self, purpose: str, agent_id: str, text: str, call_index: int | None = None) -> None:
        """Canned reply for (purpose, agent[, call_index]) - used by tests/replay fixtures."""
        if call_index is None:
            self.script[(purpose, agent_id)] = text
        else:
            self.script_by_call[(purpose, agent_id, call_index)] = text

    async def complete(self, req: LLMRequest) -> LLMResponse:
        text: str
        agent = req.agent_id or ""
        exact = self.script_by_call.get((req.purpose, agent, req.call_index))
        key = (req.purpose, agent)
        if exact is not None:
            text = exact
        elif key in self.script:
            text = self.script[key]
        elif req.purpose == "decide":
            text = self._decide_reply(req)
        elif req.purpose == "produce_artifact":
            text = json.dumps({"_mock": "artifact"})
        else:
            text = json.dumps({"_mock": req.purpose})
        tokens_in = (len(req.system) + len(req.user)) // 4
        tokens_out = len(text) // 4
        return LLMResponse(
            text=text, provider=self.id, model=self.model,
            tokens_in=tokens_in, tokens_out=tokens_out,
        )

    def _decide_reply(self, req: LLMRequest) -> str:
        rng = derive_rng(0, req.tick, "mock-decide", req.agent_id)
        action: str
        args: dict[str, object]
        if self.policy == "noop":
            action, args = "noop", {}
        elif self.policy == "adversarial":
            if rng.random() < 0.5:
                action, args = "set_balance", {"funds": 10**9}
            else:
                action, args = "take_job", {"job_id": "job_missing"}
        else:  # oracle / random_valid both produce a simple valid action
            action, args = ("noop", {}) if rng.random() < 0.3 else ("rest", {})
        return json.dumps({"action": action, "args": args, "reason": "mock"})
