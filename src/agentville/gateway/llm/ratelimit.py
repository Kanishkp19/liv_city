"""Rate limiting: sliding-60s token buckets, cooldown, circuit breaker (LLM_GATEWAY S4)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class RateLimited(Exception):
    """Provider temporarily unavailable (429/backoff); router should try next."""


@dataclass
class TokenBucket:
    """Sliding 60s window for RPM and TPM."""

    rpm: int
    tpm: int
    requests: list[float] = field(default_factory=list)
    tokens: list[tuple[float, int]] = field(default_factory=list)
    cooldown_until: float = 0.0
    consecutive_errors: int = 0
    circuit_open_until: float = 0.0
    not_found_streak: int = 0
    retired: bool = False

    def _now(self) -> float:
        return time.monotonic()

    def acquire(self, est_tokens: int) -> None:
        """Raise RateLimited if RPM/TPM/cooldown/circuit exhausted."""
        now = self._now()
        if self.retired:
            raise RateLimited("provider retired")
        if now < self.cooldown_until or now < self.circuit_open_until:
            raise RateLimited("cooldown")
        self.requests = [t for t in self.requests if now - t < 60]
        self.tokens = [(t, n) for t, n in self.tokens if now - t < 60]
        if len(self.requests) >= self.rpm:
            raise RateLimited("rpm")
        if sum(n for _, n in self.tokens) + est_tokens > self.tpm:
            raise RateLimited("tpm")
        self.requests.append(now)
        self.tokens.append((now, est_tokens))

    def record_success(self) -> None:
        self.consecutive_errors = 0
        self.not_found_streak = 0

    def record_error(self, *, retry_after: float | None = None, not_found: bool = False) -> None:
        """429 -> cooldown; 3 consecutive -> circuit exponential to 15min; 10x404 -> retire."""
        now = self._now()
        self.consecutive_errors += 1
        if not_found:
            self.not_found_streak += 1
            if self.not_found_streak >= 10:
                self.retired = True
        if retry_after is not None:
            self.cooldown_until = now + retry_after
        if self.consecutive_errors >= 3:
            backoff = min(60 * 2 ** (self.consecutive_errors - 3), 900)
            self.circuit_open_until = now + backoff
