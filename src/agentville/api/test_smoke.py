"""API smoke: world create + state + health + metrics."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agentville.api.main import app


def test_health_and_metrics() -> None:
    c = TestClient(app)
    r = c.get("/api/v1/system/health")
    assert r.status_code == 200 and "providers" in r.json()
    r = c.get("/metrics")
    assert r.status_code == 200 and "agentville_worlds" in r.text
