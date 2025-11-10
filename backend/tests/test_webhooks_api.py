"""Testes para a API de webhooks."""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress

import pytest

from app.models.webhook import WebhookEvent


@pytest.mark.asyncio
async def test_create_list_and_test_webhook(
    register_user,
    async_client_factory,
) -> None:
    response, payload = await register_user(
        plan_slug="enterprise",
        company_name="Empresa Webhook",
        document="11144477735",
    )
    assert response.status_code == 201
    tokens = response.json()["tokens"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    received_events: list[dict] = []

    async def handle_webhook(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = await reader.read(1024)
                if not chunk:
                    break
                data += chunk
            headers_block, _, body_block = data.partition(b"\r\n\r\n")
            content_length = 0
            for header_line in headers_block.decode().split("\r\n"):
                if header_line.lower().startswith("content-length:"):
                    content_length = int(header_line.split(":", 1)[1].strip())
                    break
            while len(body_block) < content_length:
                body_block += await reader.read(content_length - len(body_block))
            body = body_block[:content_length]
            received_events.append(json.loads(body.decode()))

            response_bytes = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: 15\r\n"
                "\r\n"
                '{"received":true}'
            ).encode()
            writer.write(response_bytes)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle_webhook, host="0.0.0.0", port=0)
    server_port = server.sockets[0].getsockname()[1]
    server_task = asyncio.create_task(server.serve_forever())

    try:
        async with async_client_factory(headers=headers) as client:
            create_payload = {
                "url": f"http://127.0.0.1:{server_port}/webhook-test",
                "secret": "playwright-secret",
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
            assert result["delivered"] == 1

            logs_resp = await client.get("/api/v1/webhooks/logs")
            assert logs_resp.status_code == 200
            logs = logs_resp.json()
            assert logs and logs[0]["event"] == WebhookEvent.CAMPAIGN_STARTED.value

            assert received_events, "Webhook de teste não foi recebido pelo servidor fake."
            assert received_events[0]["event"] == WebhookEvent.CAMPAIGN_STARTED.value

            delete_resp = await client.delete(f"/api/v1/webhooks/{subscription['id']}")
            assert delete_resp.status_code == 204

            empty_resp = await client.get("/api/v1/webhooks")
            assert empty_resp.json() == []
    finally:
        server.close()
        await server.wait_closed()
        server_task.cancel()
        with suppress(asyncio.CancelledError):
            await server_task


