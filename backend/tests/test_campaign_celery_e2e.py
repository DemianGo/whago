"""Teste end-to-end do fluxo de campanhas com Celery e Baileys reais."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.engine.url import make_url

from app.database import AsyncSessionLocal, DATABASE_URL_RAW_ADJUSTED
import pytest

from app.models.campaign import (
    Campaign,
    CampaignContact,
    CampaignMessage,
    CampaignStatus,
    CampaignType,
    MessageStatus,
)
from app.models.chip import Chip, ChipStatus
from app.models.user import User
from tasks import campaign_tasks

pytestmark = pytest.mark.asyncio(loop_scope="session")


SYNC_ENGINE = create_engine(
    make_url(DATABASE_URL_RAW_ADJUSTED).set(drivername="postgresql+psycopg2")
)


def _seed_campaign_sync(user_id: UUID) -> UUID:
    with Session(SYNC_ENGINE) as session:
        user = session.get(User, user_id)
        if user is None:
            raise RuntimeError("Usuário não encontrado para seed de campanha.")
        chip = Chip(
            user_id=user.id,
            alias=f"Chip {uuid4().hex[:6]}",
            session_id=f"session-{uuid4().hex[:8]}",
            status=ChipStatus.CONNECTED,
        )
        session.add(chip)
        session.flush()

        campaign = Campaign(
            user_id=user.id,
            name="Campanha Celery",
            description="Fluxo completo Celery/Baileys",
            type=CampaignType.SIMPLE,
            status=CampaignStatus.DRAFT,
            message_template="Olá {{name}}",
            settings={"chip_ids": [str(chip.id)]},
        )
        session.add(campaign)
        session.flush()

        contact = CampaignContact(
            campaign_id=campaign.id,
            phone_number="5511999999998",
            name="Contato Celery",
        )
        session.add(contact)
        session.commit()
        return campaign.id


async def _seed_campaign(user_id: UUID) -> UUID:
    return await asyncio.to_thread(_seed_campaign_sync, user_id)


async def _fetch_campaign(campaign_id: UUID) -> Campaign:
  async with AsyncSessionLocal() as session:
      campaign = await session.get(Campaign, campaign_id)
      await session.refresh(campaign)
      return campaign


async def _fetch_messages(campaign_id: UUID) -> list[CampaignMessage]:
  async with AsyncSessionLocal() as session:
      result = await session.execute(
          select(CampaignMessage).where(CampaignMessage.campaign_id == campaign_id)
      )
      return result.scalars().all()


@pytest.mark.asyncio
async def test_campaign_dispatch_end_to_end(register_user, async_client_factory, monkeypatch) -> None:
  response, _ = await register_user(
      plan_slug="business",
      company_name="Empresa Celery",
      document="11144477735",
  )
  assert response.status_code == 201, response.text
  tokens = response.json()["tokens"]
  headers = {"Authorization": f"Bearer {tokens['access_token']}"}
  user_id = UUID(response.json()["user"]["id"])

  campaign_id = await _seed_campaign(user_id)

  async with async_client_factory(headers=headers) as client:
      start_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/start")
      assert start_resp.status_code == 200, start_resp.text

  with Session(SYNC_ENGINE) as session:
      campaign = session.get(Campaign, campaign_id)
      assert campaign is not None
      assert campaign.status == CampaignStatus.RUNNING

