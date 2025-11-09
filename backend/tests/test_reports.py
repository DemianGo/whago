"""Testes para os relatórios avançados e exportações."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

import asyncio
import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.campaign import (
    Campaign,
    CampaignContact,
    CampaignMessage,
    CampaignStatus,
    CampaignType,
    MessageStatus,
)
from app.models.chip import Chip, ChipEvent, ChipEventType, ChipStatus
from app.models.credit import CreditLedger, CreditSource
from app.models.invoice import Invoice, InvoiceStatus
from app.models.plan import Plan
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User

url = make_url(settings.database_url)
SYNC_ENGINE = create_engine(
    url.set(drivername="postgresql+psycopg2", host="postgres")
)

pytestmark = pytest.mark.asyncio


def _seed_reporting_data_sync(user_id: UUID) -> UUID:
    with Session(SYNC_ENGINE) as session:
        user = session.get(User, user_id)
        if user is None:
            raise RuntimeError("Usuário inexistente para seed de relatórios.")

        plan = session.execute(select(Plan).where(Plan.slug == "business")).scalar_one()
        if plan and user.plan_id != plan.id:
            user.plan_id = plan.id

        campaign = Campaign(
            user_id=user.id,
            name="Campanha QA",
            description="Campanha de teste",
            type=CampaignType.SIMPLE,
            status=CampaignStatus.COMPLETED,
            message_template="Olá {{name}}",
            total_contacts=1,
            sent_count=1,
            delivered_count=1,
            read_count=0,
            failed_count=0,
            credits_consumed=1,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            completed_at=datetime.now(timezone.utc),
        )
        session.add(campaign)
        session.flush()

        contact = CampaignContact(
            campaign_id=campaign.id,
            phone_number="+551199999999",
            name="Contato QA",
        )
        session.add(contact)
        session.flush()

        alias_suffix = uuid4().hex[:4]
        chip = Chip(
            user_id=user.id,
            alias=f"Chip QA {alias_suffix}",
            session_id=f"session-{alias_suffix}",
            status=ChipStatus.CONNECTED,
            health_score=95,
        )
        session.add(chip)
        session.flush()

        message = CampaignMessage(
            campaign_id=campaign.id,
            contact_id=contact.id,
            chip_id=chip.id,
            content="Mensagem de teste",
            status=MessageStatus.DELIVERED,
            sent_at=datetime.now(timezone.utc) - timedelta(minutes=4),
            delivered_at=datetime.now(timezone.utc) - timedelta(minutes=3),
        )
        session.add(message)

        chip_event = ChipEvent(
            chip_id=chip.id,
            type=ChipEventType.MESSAGE_SENT,
            description="Mensagem enviada",
        )
        session.add(chip_event)

        transaction = Transaction(
            user_id=user.id,
            type=TransactionType.CREDIT_PURCHASE,
            status=TransactionStatus.COMPLETED,
            amount=30,
            credits=1000,
            payment_method="pix",
            reference_code=f"PIX-{uuid4().hex[:6]}",
        )
        session.add(transaction)
        session.flush()

        user.credits += 1000

        ledger_entry = CreditLedger(
            user_id=user.id,
            transaction_id=transaction.id,
            source=CreditSource.PURCHASE,
            amount=1000,
            balance_after=user.credits,
            description="Compra de créditos",
        )
        session.add(ledger_entry)

        invoice = Invoice(
            transaction_id=transaction.id,
            user_id=user.id,
            number=f"TEST-{uuid4().hex[:6]}",
            status=InvoiceStatus.PAID,
            amount=30,
            pdf_url="https://billing.whago.local/invoices/test.pdf",
        )
        session.add(invoice)

        session.commit()
        return campaign.id


async def seed_reporting_data(user_id: UUID) -> UUID:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _seed_reporting_data_sync, user_id)


@pytest.mark.asyncio
async def test_campaign_report_export(register_user, base_url: str) -> None:
    response, payload = await register_user()
    tokens = response.json()["tokens"]
    user_id = UUID(response.json()["user"]["id"])

    campaign_id = await seed_reporting_data(user_id)

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        json_resp = await client.get(f"/api/v1/reports/campaign/{campaign_id}")
        assert json_resp.status_code == 200, json_resp.text
        body = json_resp.json()
        assert body["name"] == "Campanha QA"
        assert body["sent"] == 1

        csv_resp = await client.get(f"/api/v1/reports/campaign/{campaign_id}?format=csv")
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.headers["content-type"]
        assert "+551199999999" in csv_resp.text


@pytest.mark.asyncio
async def test_financial_and_chips_reports(register_user, base_url: str) -> None:
    response, payload = await register_user()
    tokens = response.json()["tokens"]
    user_id = UUID(response.json()["user"]["id"])

    await seed_reporting_data(user_id)

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        chips_json = await client.get("/api/v1/reports/chips")
        assert chips_json.status_code == 200, chips_json.text

        chips_pdf = await client.get("/api/v1/reports/chips?format=pdf")
        assert chips_pdf.status_code == 200
        assert chips_pdf.headers["content-type"].startswith("application/pdf")

        financial_xlsx = await client.get("/api/v1/reports/financial?format=xlsx")
        assert financial_xlsx.status_code == 200, financial_xlsx.text if financial_xlsx.content else ""


@pytest.mark.asyncio
async def test_plan_comparison_exports(register_user, base_url: str) -> None:
    response, payload = await register_user()
    tokens = response.json()["tokens"]

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    async with httpx.AsyncClient(base_url=base_url, headers=headers) as client:
        json_resp = await client.get("/api/v1/reports/plans/comparison")
        assert json_resp.status_code == 200
        data = json_resp.json()
        assert data["plans"], "Deve retornar planos cadastrados"

        pdf_resp = await client.get("/api/v1/reports/plans/comparison?format=pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"].startswith("application/pdf")
