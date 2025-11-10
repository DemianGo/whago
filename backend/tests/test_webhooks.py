"""Testes para integração com webhooks externos."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import DATABASE_URL
from app.models.campaign import Campaign, CampaignContact, CampaignStatus, CampaignType
from app.models.chip import Chip, ChipStatus
from app.models.invoice import Invoice
from app.models.plan import Plan
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.models.webhook import WebhookDeliveryLog, WebhookEvent, WebhookSubscription
from app.services.billing_service import BillingService
from app.services.campaign_service import CampaignService
from app.services.payment_gateway import PaymentGatewayClient, PaymentResult
from app.services.webhook_service import WebhookService


async def _create_enterprise_user(session: AsyncSession) -> User:
    plan = await session.scalar(select(Plan).where(Plan.slug == "enterprise"))
    user = User(
        name="Usuário Enterprise",
        email=f"webhook-{uuid4().hex[:8]}@example.com",
        password_hash="hashed",
        phone="+551199999999",
        company_name="Empresa Webhook",
        document="11144477735",
        plan=plan,
        credits=500,
        is_active=True,
        is_verified=True,
        default_payment_method="card",
        billing_customer_reference=f"cust-{uuid4().hex[:6]}",
        subscription_renewal_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


class StubGateway(PaymentGatewayClient):
    """Gateway de testes que sempre aprova a cobrança."""

    async def charge_subscription(self, *, user: User, plan: Plan, amount):
        return PaymentResult(
            success=True,
            provider="stripe",
            transaction_reference=f"tx-{uuid4().hex[:10]}",
            response_code="200",
            message="Cobrança aprovada",
        )


def _with_session(fn):
    async def runner() -> None:
        engine = create_async_engine(DATABASE_URL, future=True)
        SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
        try:
            async with SessionLocal() as session:
                await fn(session)
        finally:
            await engine.dispose()

    asyncio.run(runner())


def test_webhook_service_dispatch_success() -> None:
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"received": True})

    transport = httpx.MockTransport(handler)

    async def scenario(session: AsyncSession) -> None:
        user = await _create_enterprise_user(session)
        service = WebhookService(
            session,
            client_factory=lambda: httpx.AsyncClient(transport=transport, timeout=10.0),
        )

        subscription = await service.create_subscription(
            user_id=user.id,
            url="https://hooks.example.com/webhook",
            events=[WebhookEvent.CAMPAIGN_STARTED],
            secret="super-secret",
        )

        delivered = await service.dispatch(
            user_id=user.id,
            event=WebhookEvent.CAMPAIGN_STARTED,
            payload={"campaign_id": "123", "name": "Campanha Teste"},
        )
        assert delivered == 1
        assert len(calls) == 1

        request = calls[0]
        assert request.headers["X-Webhook-Event"] == "campaign.started"
        body = request.content
        expected_signature = hmac.new(
            b"super-secret", msg=body, digestmod=hashlib.sha256
        ).hexdigest()
        assert request.headers["X-Webhook-Signature"] == expected_signature

        payload = json.loads(body)
        assert payload["event"] == "campaign.started"
        assert payload["data"]["campaign_id"] == "123"

        result = await session.execute(
            select(WebhookDeliveryLog).where(WebhookDeliveryLog.subscription_id == subscription.id)
        )
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].success is True
        assert logs[0].status_code == 200

        await session.execute(delete(WebhookDeliveryLog).where(WebhookDeliveryLog.subscription_id == subscription.id))
        await session.execute(delete(WebhookSubscription).where(WebhookSubscription.id == subscription.id))
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()

    _with_session(scenario)


def test_webhook_service_dispatch_failure_logged() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(handler)

    async def scenario(session: AsyncSession) -> None:
        user = await _create_enterprise_user(session)
        service = WebhookService(
            session,
            client_factory=lambda: httpx.AsyncClient(transport=transport, timeout=1.0),
        )
        subscription = await service.create_subscription(
            user_id=user.id,
            url="https://hooks.example.com/failure",
            events=[WebhookEvent.CAMPAIGN_COMPLETED],
        )

        delivered = await service.dispatch(
            user_id=user.id,
            event=WebhookEvent.CAMPAIGN_COMPLETED,
            payload={"campaign_id": "456"},
        )
        assert delivered == 0

        result = await session.execute(
            select(WebhookDeliveryLog).where(WebhookDeliveryLog.subscription_id == subscription.id)
        )
        logs = result.scalars().all()
        assert logs and logs[0].success is False
        assert logs[0].status_code is None
        assert "connection refused" in (logs[0].response_body or "")

        await session.execute(delete(WebhookDeliveryLog).where(WebhookDeliveryLog.subscription_id == subscription.id))
        await session.execute(delete(WebhookSubscription).where(WebhookSubscription.id == subscription.id))
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()

    _with_session(scenario)


def test_campaign_start_triggers_webhook(monkeypatch) -> None:
    captured: list[tuple[UUID, str, dict]] = []

    class DummyWebhook:
        def __init__(self, session: AsyncSession) -> None:
            self.session = session

        async def dispatch(self, *, user_id: UUID, event: str, payload: dict) -> int:
            captured.append((user_id, event, payload))
            return 1

    monkeypatch.setattr("app.services.campaign_service.WebhookService", DummyWebhook)
    monkeypatch.setattr("app.services.campaign_service.start_campaign_dispatch.delay", lambda *_, **__: None)
    monkeypatch.setattr("app.services.campaign_service.resume_campaign_dispatch.delay", lambda *_, **__: None)

    async def scenario(session: AsyncSession) -> None:
        user = await _create_enterprise_user(session)

        chip = Chip(
            user_id=user.id,
            alias=f"Chip {uuid4().hex[:4]}",
            session_id=f"session-{uuid4().hex[:6]}",
            status=ChipStatus.CONNECTED,
        )
        session.add(chip)
        await session.flush()

        campaign = Campaign(
            user_id=user.id,
            name="Campanha Webhook",
            description="Teste de webhooks",
            type=CampaignType.SIMPLE,
            status=CampaignStatus.DRAFT,
            message_template="Olá {{name}}",
            settings={"chip_ids": [str(chip.id)]},
        )
        session.add(campaign)
        await session.flush()

        contact = CampaignContact(
            campaign_id=campaign.id,
            phone_number="5511999998888",
            name="Contato QA",
        )
        session.add(contact)
        await session.commit()
        await session.refresh(user, attribute_names=["plan"])
        await session.refresh(campaign)

        service = CampaignService(session)
        response = await service.start_campaign(user, campaign.id)
        assert response.status == CampaignStatus.RUNNING
        assert captured, "Webhook deve ser disparado ao iniciar campanha."

        event_user, event_name, payload = captured[0]
        assert event_user == user.id
        assert event_name == WebhookEvent.CAMPAIGN_STARTED.value
        assert payload["campaign_id"] == str(campaign.id)
        assert payload["status"] == CampaignStatus.RUNNING.value

        await session.execute(delete(CampaignContact).where(CampaignContact.campaign_id == campaign.id))
        await session.execute(delete(Campaign).where(Campaign.id == campaign.id))
        await session.execute(delete(Chip).where(Chip.id == chip.id))
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()

    _with_session(scenario)


def test_payment_success_triggers_webhook(monkeypatch) -> None:
    captured: list[tuple[UUID, str, dict]] = []

    class DummyWebhook:
        def __init__(self, session: AsyncSession) -> None:
            self.session = session

        async def dispatch(self, *, user_id: UUID, event: str, payload: dict) -> int:
            captured.append((user_id, event, payload))
            return 1

    monkeypatch.setattr("app.services.billing_service.WebhookService", DummyWebhook)

    async def scenario(session: AsyncSession) -> None:
        user = await _create_enterprise_user(session)
        subscription = WebhookSubscription(
            user_id=user.id,
            url="https://hooks.example.com/billing",
            events=[WebhookEvent.PAYMENT_SUCCEEDED.value],
            is_active=True,
        )
        session.add(subscription)
        await session.commit()

        gateway = StubGateway()
        service = BillingService(session, gateway=gateway)
        await service.process_subscription_cycle()

        assert captured, "Webhook deve ser disparado após pagamento aprovado."
        event_user, event_name, payload = captured[0]
        assert event_user == user.id
        assert event_name == WebhookEvent.PAYMENT_SUCCEEDED.value
        assert float(payload["amount"]) >= 0
        assert payload["plan"] == "enterprise"

        await session.execute(delete(WebhookSubscription).where(WebhookSubscription.id == subscription.id))
        await session.execute(delete(WebhookDeliveryLog).where(WebhookDeliveryLog.user_id == user.id))
        await session.execute(delete(Invoice).where(Invoice.user_id == user.id))
        await session.execute(delete(Transaction).where(Transaction.user_id == user.id))
        await session.execute(delete(User).where(User.id == user.id))
        await session.commit()

    _with_session(scenario)


