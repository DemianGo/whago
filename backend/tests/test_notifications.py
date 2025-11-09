"""Testes para notificações in-app."""

from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import settings
from app.models.notification import Notification, NotificationType


pytestmark = pytest.mark.asyncio


url = make_url(settings.database_url)
SYNC_ENGINE = create_engine(url.set(drivername="postgresql+psycopg2", host="postgres"))


async def _seed_notifications(user_id: UUID, *, count: int = 3) -> None:
    with Session(SYNC_ENGINE) as session:
        for idx in range(count):
            notification = Notification(
                user_id=user_id,
                title=f"Notificação {idx + 1}",
                message=f"Mensagem {idx + 1}",
                type=NotificationType.INFO if idx % 2 == 0 else NotificationType.WARNING,
            )
            session.add(notification)
        session.commit()


async def test_list_and_mark_notifications(register_user, base_url: str) -> None:
    response, _ = await register_user()
    assert response.status_code == 201
    tokens = response.json()["tokens"]
    user_id = UUID(response.json()["user"]["id"])

    await _seed_notifications(user_id, count=3)

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        unread_resp = await client.get("/api/v1/notifications/unread-count")
        assert unread_resp.status_code == 200
        assert unread_resp.json()["unread"] == 3

        list_resp = await client.get("/api/v1/notifications", params={"limit": 5})
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) == 3
        ids = [UUID(item["id"]) for item in items[:2]]

        mark_resp = await client.post(
            "/api/v1/notifications/mark-read",
            json={"notification_ids": [str(i) for i in ids]},
        )
        assert mark_resp.status_code == 200
        assert mark_resp.json()["unread"] == 1

        mark_all = await client.post("/api/v1/notifications/mark-all-read")
        assert mark_all.status_code == 200
        assert mark_all.json()["unread"] == 0

        final_list = await client.get("/api/v1/notifications", params={"unread_only": True})
        assert final_list.status_code == 200
        assert final_list.json() == []
