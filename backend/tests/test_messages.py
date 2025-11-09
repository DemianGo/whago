"""Testes para o endpoint consolidado de mensagens."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import settings
from app.models.campaign import Campaign, CampaignContact, CampaignMessage, CampaignStatus, CampaignType, MessageStatus


pytestmark = pytest.mark.asyncio


url = make_url(settings.database_url)
SYNC_ENGINE = create_engine(url.set(drivername="postgresql+psycopg2", host="postgres"))


async def _seed_message(user_id: UUID) -> tuple[UUID, str]:
    with Session(SYNC_ENGINE) as session:
        campaign = Campaign(
            user_id=user_id,
            name="Campanha QA",
            description="Campanha de teste",
            type=CampaignType.SIMPLE,
            status=CampaignStatus.RUNNING,
            message_template="Olá",
            total_contacts=1,
            sent_count=1,
        )
        session.add(campaign)
        session.flush()

        contact = CampaignContact(
            campaign_id=campaign.id,
            phone_number="+551199999999",
        )
        session.add(contact)
        session.flush()

        message = CampaignMessage(
            campaign_id=campaign.id,
            contact_id=contact.id,
            status=MessageStatus.SENT,
            content="Olá mundo",
            sent_at=datetime.now(timezone.utc),
            delivered_at=datetime.now(timezone.utc),
            read_at=None,
        )
        session.add(message)
        session.commit()
        return campaign.id, contact.phone_number


async def test_messages_endpoint(register_user, base_url: str) -> None:
    response, _ = await register_user()
    assert response.status_code == 201
    tokens = response.json()["tokens"]
    user_id = UUID(response.json()["user"]["id"])

    campaign_id, phone_number = await _seed_message(user_id)

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        list_resp = await client.get("/api/v1/messages", params={"limit": 10})
        assert list_resp.status_code == 200
        payload = list_resp.json()
        assert payload, "Deve retornar ao menos uma mensagem"
        assert payload[0]["recipient"] == phone_number

        filter_resp = await client.get(
            "/api/v1/messages",
            params={"status": "sent", "campaign_id": str(campaign_id)},
        )
        assert filter_resp.status_code == 200
        filtered = filter_resp.json()
        assert all(item["status"] == MessageStatus.SENT.value for item in filtered)
