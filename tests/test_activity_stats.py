"""GET /api/activity/stats: full-log aggregate counts, added because the
Overview page's KPIs/charts were undercounting by reading only the most
recent 100 decision-log rows (a bulk action like running signal detection
alone logs ~84 events and pushes older rows out of that window)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_activity_stats_shape():
    resp = client.get("/api/activity/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"total", "by_agent", "by_action"}
    assert isinstance(body["by_agent"], dict)
    assert isinstance(body["by_action"], dict)
    assert body["total"] == sum(body["by_agent"].values())
    assert body["total"] == sum(body["by_action"].values())
