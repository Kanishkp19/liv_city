"""Web study gateway: allowlisted GET-only fetch, sanitized, injection-flagged (SECURITY S3)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from agentville.config import load_allowlist


def domain_allowed(url: str, allowlist: list[str] | None = None) -> bool:
    """Registrable-domain suffix match against allowlist; HTTPS only, GET only by construction."""
    cfg = allowlist or load_allowlist().get("domains", [])
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in cfg)


def sanitize_html(raw: str) -> str:
    """Strip scripts/styles/tags to text; truncate to 4000 chars."""
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:4000]


INJECTION_HEURISTICS = [
    "ignore previous", "ignore all previous", "system prompt", "you are now",
    "disregard the above", "new instructions:",
]


def injection_flags(text: str) -> list[str]:
    """Flag instruction-like phrases; flagged text still passes wrapped in <untrusted>."""
    low = text.lower()
    return [h for h in INJECTION_HEURISTICS if h in low]


def fetch_study_page(url: str, *, allowlist: list[str] | None = None) -> dict[str, object]:
    """Synchronous GET (httpx) with allowlist+size cap; returns row-shaped dict, fail closed."""
    from agentville.gateway.web import _USER_AGENT

    row: dict[str, object] = {"url": url, "domain": urlparse(url).hostname or "",
                              "allowed": False, "http_status": None, "bytes": None,
                              "sanitized_text": None, "injection_flags": None}
    if not domain_allowed(url, allowlist):
        return row
    try:
        import httpx

        with httpx.Client(timeout=10, follow_redirects=True, headers={"User-Agent": _USER_AGENT}) as client:
            r = client.get(url)
        row["http_status"] = r.status_code
        if r.status_code != 200:
            return row
        raw = r.text[:1_048_576]
        clean = sanitize_html(raw)
        flags = injection_flags(clean)
        row.update({"allowed": True, "bytes": len(raw), "sanitized_text": clean,
                    "injection_flags": ",".join(flags) if flags else None})
        return row
    except Exception as e:  # noqa: BLE001
        row["injection_flags"] = f"fetch_error:{type(e).__name__}"
        return row
