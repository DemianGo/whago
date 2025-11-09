"""
Testes para os endpoints de dashboard.
"""

from __future__ import annotations

from datetime import datetime

import httpx
import pytest

pytestmark = pytest.mark.asyncio


async def test_dashboard_summary(register_user, base_url: str) -> None:
    """Resumo deve trazer estrutura e valores padrões para novo usuário."""

    register_response, _ = await register_user()
    tokens = register_response.json()["tokens"]

    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    ) as client:
        response = await client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    data = response.json()

    expected_keys = {
        "credits_available",
        "messages_today",
        "messages_today_variation",
        "messages_month",
        "messages_month_variation",
        "success_rate",
        "chips_connected",
        "chips_total",
        "campaigns_active",
        "campaigns_total",
    }
    assert expected_keys.issubset(data.keys())
    assert data["credits_available"] == 100
    assert data["messages_today"] == 0
    assert data["messages_month"] == 0
    assert data["success_rate"] == 0.0
    assert data["chips_connected"] == 0
    assert data["chips_total"] == 0
    assert data["campaigns_active"] == 0
    assert data["campaigns_total"] == 0


async def test_dashboard_trend_and_activity(register_user, base_url: str) -> None:
    """Trend e activity retornam estruturas válidas mesmo sem dados."""

    register_response, _ = await register_user()
    tokens = register_response.json()["tokens"]

    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    ) as client:
        trend_response = await client.get("/api/v1/dashboard/messages-trend")
        activity_response = await client.get("/api/v1/dashboard/activity")

    assert trend_response.status_code == 200
    trend = trend_response.json()
    assert "points" in trend
    assert len(trend["points"]) == 30
    for point in trend["points"]:
        datetime.fromisoformat(point["date"])
        assert {"sent", "delivered", "read", "failed"} <= set(point.keys())

    assert activity_response.status_code == 200
    activity = activity_response.json()
    assert "items" in activity
    assert activity["items"] == []

