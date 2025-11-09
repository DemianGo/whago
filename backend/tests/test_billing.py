"""
Testes de billing conforme requisitos do PRD.
"""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.transaction import TransactionType
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def test_upgrade_plan_and_schedule_downgrade(register_user, base_url: str) -> None:
    response, payload = await register_user()
    tokens = response.json()["tokens"]

    async with httpx.AsyncClient(
        base_url=base_url, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ) as client:
        upgrade = await client.post(
            "/api/v1/billing/plan/change",
            json={"plan_slug": "business", "payment_method": "card"},
        )
    assert upgrade.status_code == 200
    upgrade_body = upgrade.json()
    assert upgrade_body["status"] in {"subscribed", "upgraded"}
    assert upgrade_body["current_plan"] == "business"
    assert upgrade_body["renewal_at"] is not None

    async with httpx.AsyncClient(
        base_url=base_url, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ) as client:
        status_resp = await client.get("/api/v1/billing/subscription")
    assert status_resp.status_code == 200
    assert status_resp.json()["current_plan"] == "business"

    async with httpx.AsyncClient(
        base_url=base_url, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ) as client:
        downgrade = await client.post(
            "/api/v1/billing/plan/change",
            json={"plan_slug": "free", "payment_method": "card"},
        )
    assert downgrade.status_code == 200
    downgrade_body = downgrade.json()
    assert downgrade_body["status"] == "scheduled_downgrade"
    assert downgrade_body["pending_plan"] == "free"

    async with httpx.AsyncClient(
        base_url=base_url, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ) as client:
        status_after_downgrade = await client.get("/api/v1/billing/subscription")
    assert status_after_downgrade.status_code == 200
    body_after = status_after_downgrade.json()
    assert body_after["current_plan"] == "business"
    assert body_after["pending_plan"] == "free"


async def test_cancel_downgrade_and_purchase_credits(register_user, base_url: str) -> None:
    response, payload = await register_user()
    tokens = response.json()["tokens"]

    async with httpx.AsyncClient(
        base_url=base_url, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ) as client:
        await client.post(
            "/api/v1/billing/plan/change",
            json={"plan_slug": "business", "payment_method": "card"},
        )
        await client.post(
            "/api/v1/billing/plan/change",
            json={"plan_slug": "free", "payment_method": "card"},
        )
        cancel = await client.post("/api/v1/billing/plan/downgrade/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    from uuid import uuid4

    purchase_payload = {
        "package_code": "credits_1000",
        "payment_method": "pix",
        "payment_reference": f"PIX-{uuid4().hex[:12]}",
    }
    async with httpx.AsyncClient(
        base_url=base_url, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ) as client:
        purchase = await client.post("/api/v1/billing/credits/purchase", json=purchase_payload)
    assert purchase.status_code == 201
    purchase_body = purchase.json()
    assert purchase_body["credits_added"] == 1000
    assert purchase_body["payment_status"] == "completed"

    async with httpx.AsyncClient(
        base_url=base_url, headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ) as client:
        transactions = await client.get("/api/v1/billing/transactions")
        history = await client.get("/api/v1/billing/credits/history")
        profile = await client.get("/api/v1/users/me")
    assert transactions.status_code == 200
    assert history.status_code == 200
    assert profile.status_code == 200
    assert profile.json()["credits"] == 1100
    tx_list = transactions.json()
    assert any(tx["type"] == TransactionType.CREDIT_PURCHASE.value for tx in tx_list)
    credit_entries = history.json()
    assert len(credit_entries) >= 1


