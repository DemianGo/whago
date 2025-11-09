"""Testes da API de auditoria."""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest

from app.database import AsyncSessionLocal
from app.services.audit_service import AuditService


pytestmark = pytest.mark.asyncio


async def _create_manual_log(user_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        service = AuditService(session)
        await service.record(
            user_id=user_id,
            action="custom.event",
            entity_type="test",
            entity_id="manual",
            description="Log manual para teste",
            extra_data={"origin": "test"},
            auto_commit=False,
        )
        await session.commit()


async def test_audit_logs_endpoint(register_user, base_url: str) -> None:
    response, payload = await register_user()
    assert response.status_code == 201
    tokens = response.json()["tokens"]
    user_id = UUID(response.json()["user"]["id"])

    # Força um login adicional para gerar novo log
    async with httpx.AsyncClient(base_url=base_url) as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        assert login_resp.status_code == 200

    await _create_manual_log(user_id)

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        list_resp = await client.get("/api/v1/audit", params={"limit": 10})
        assert list_resp.status_code == 200
        logs = list_resp.json()
        assert logs, "Deve retornar ao menos um log de auditoria"
        actions = {entry["action"] for entry in logs}
        assert "user.registered" in actions
        assert "custom.event" in actions

        filter_resp = await client.get("/api/v1/audit", params={"action": "custom.event"})
        assert filter_resp.status_code == 200
        filtered = filter_resp.json()
        assert all(entry["action"] == "custom.event" for entry in filtered)
