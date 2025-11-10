"""Testes para a API de webhooks."""

from __future__ import annotations

import pytest

from app.models.webhook import WebhookEvent


@pytest.mark.asyncio
async def test_create_list_and_test_webhook(
    register_user,
    async_client_factory,
    monkeypatch,
) -> None:
    response, payload = await register_user(
        plan_slug="enterprise",
        company_name="Empresa Webhook",
        document="11144477735",
    )
    assert response.status_code == 201
    tokens = response.json()["tokens"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    async def fake_test_event(self, *, user_id, subscription_id, event, payload):
        return 0

    monkeypatch.setattr(
        "app.services.webhook_service.WebhookService.test_event",
        fake_test_event,
    )

    async with async_client_factory(headers=headers) as client:
        create_payload = {
            "url": "https://webhooks.example.com/whago",
            "secret": "super-secret",
            "events": [WebhookEvent.CAMPAIGN_STARTED.value],
            "is_active": True,
        }
        create_resp = await client.post("/api/v1/webhooks", json=create_payload)
        assert create_resp.status_code == 201, create_resp.text
        subscription = create_resp.json()
        assert subscription["url"] == create_payload["url"]
        assert subscription["events"] == create_payload["events"]

        list_resp = await client.get("/api/v1/webhooks")
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) == 1

        test_resp = await client.post(
            "/api/v1/webhooks/test",
            json={
                "subscription_id": subscription["id"],
                "event": WebhookEvent.CAMPAIGN_STARTED.value,
                "payload": {"campaign_id": "123"},
            },
        )
        assert test_resp.status_code == 200
        result = test_resp.json()
        assert result["delivered"] >= 0

        logs_resp = await client.get("/api/v1/webhooks/logs")
        assert logs_resp.status_code == 200
        logs = logs_resp.json()
        assert isinstance(logs, list)

        delete_resp = await client.delete(f"/api/v1/webhooks/{subscription['id']}")
        assert delete_resp.status_code == 204

        empty_resp = await client.get("/api/v1/webhooks")
        assert empty_resp.json() == []


