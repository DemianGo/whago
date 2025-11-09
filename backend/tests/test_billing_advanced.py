"""Testes de billing avançado (assinaturas, invoices e downgrades)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import DATABASE_URL
from app.models.invoice import Invoice
from app.models.plan import Plan
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User
from app.services.billing_service import BillingService, SUBSCRIPTION_CYCLE_DAYS
from app.services.payment_gateway import PaymentGatewayClient, PaymentResult


class FakeGateway(PaymentGatewayClient):
    """Gateway configurável para simular sucesso/falha."""

    def __init__(self, *, succeed: bool = True, fail_until: int = 0):
        super().__init__()
        self.succeed = succeed
        self.fail_until = fail_until
        self.calls = 0

    async def charge_subscription(self, *, user: User, plan: Plan, amount):
        self.calls += 1
        if self.fail_until and self.calls <= self.fail_until:
            return PaymentResult(
                success=False,
                provider="stripe",
                transaction_reference=None,
                response_code="402",
                message="Pagamento recusado",
            )
        if not self.succeed:
            return PaymentResult(
                success=False,
                provider="stripe",
                transaction_reference=None,
                response_code="402",
                message="Pagamento recusado",
            )
        return PaymentResult(
            success=True,
            provider="stripe",
            transaction_reference=f"tx-{uuid4().hex[:10]}",
            response_code="200",
            message="Cobrança aprovada",
        )


def _random_email() -> str:
    return f"test-{uuid4().hex[:8]}@example.com"


async def _create_user_with_plan(session: AsyncSession, plan_slug: str = "business") -> User:
    plan = await session.scalar(select(Plan).where(Plan.slug == plan_slug))
    user = User(
        name="Usuário Billing",
        email=_random_email(),
        password_hash="hashed-password",
        phone="+551199999999",
        company_name="Empresa QA",
        document="00000000000",
        plan=plan,
        credits=100,
        is_active=True,
        is_verified=True,
        default_payment_method="card",
        billing_customer_reference=f"cust-{uuid4().hex[:6]}",
        subscription_renewal_at=datetime.now(timezone.utc) + timedelta(days=SUBSCRIPTION_CYCLE_DAYS),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _with_session(fn) -> None:
    engine = create_async_engine(DATABASE_URL, future=True)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with SessionLocal() as session:
            await fn(session)
    finally:
        await engine.dispose()


def test_subscription_cycle_success() -> None:
    async def scenario(session: AsyncSession) -> None:
        user = await _create_user_with_plan(session, "business")
        user.subscription_renewal_at = datetime.now(timezone.utc) - timedelta(days=1)
        await session.commit()

        gateway = FakeGateway(succeed=True)
        service = BillingService(session, gateway=gateway)
        await service.process_subscription_cycle()

        await session.refresh(user, attribute_names=["plan"])
        assert user.failed_payment_attempts == 0
        assert user.subscription_renewal_at > datetime.now(timezone.utc)

        tx_result = await session.execute(
            select(Transaction)
            .where(Transaction.user_id == user.id, Transaction.type == TransactionType.SUBSCRIPTION)
            .order_by(Transaction.created_at.desc())
        )
        transaction = tx_result.scalars().first()
        assert transaction is not None
        assert transaction.status == TransactionStatus.COMPLETED

        invoice_result = await session.execute(select(Invoice).where(Invoice.user_id == user.id))
        invoices = invoice_result.scalars().all()
        assert invoices, "Uma nota fiscal deve ser gerada após a cobrança."

        txs_result = await session.execute(
            select(Transaction).where(Transaction.user_id == user.id)
        )
        transactions_to_remove = txs_result.scalars().all()
        for invoice in invoices:
            await session.delete(invoice)
        for tx in transactions_to_remove:
            await session.delete(tx)
        await session.delete(user)
        await session.commit()

    asyncio.run(_with_session(scenario))


def test_subscription_failures_trigger_suspension() -> None:
    async def scenario(session: AsyncSession) -> None:
        user = await _create_user_with_plan(session, "business")
        user.subscription_renewal_at = datetime.now(timezone.utc) - timedelta(days=1)
        await session.commit()

        gateway = FakeGateway(succeed=False, fail_until=10)
        service = BillingService(session, gateway=gateway)

        for _ in range(3):
            await service.process_subscription_cycle()

        await session.refresh(user, attribute_names=["plan", "pending_plan"])
        assert user.failed_payment_attempts >= 3
        assert user.is_suspended is True
        assert user.pending_plan is not None and user.pending_plan.slug == "free"
        assert user.billing_suspension_started_at is not None

        txs_result = await session.execute(
            select(Transaction).where(Transaction.user_id == user.id)
        )
        invoices_result = await session.execute(select(Invoice).where(Invoice.user_id == user.id))
        for invoice in invoices_result.scalars().all():
            await session.delete(invoice)
        for tx in txs_result.scalars().all():
            await session.delete(tx)
        await session.delete(user)
        await session.commit()

    asyncio.run(_with_session(scenario))


def test_pending_downgrade_after_grace_period() -> None:
    async def scenario(session: AsyncSession) -> None:
        user = await _create_user_with_plan(session, "business")
        free_plan = await session.scalar(select(Plan).where(Plan.slug == "free"))
        user.pending_plan_id = free_plan.id if free_plan else None
        user.billing_suspension_started_at = datetime.now(timezone.utc) - timedelta(days=8)
        user.is_suspended = True
        await session.commit()

        service = BillingService(session)
        await service.process_pending_downgrades()
        await session.refresh(user, attribute_names=["plan"])
        assert user.plan and user.plan.slug == "free"
        assert user.pending_plan_id is None
        assert user.is_suspended is False
        assert user.billing_suspension_started_at is None

        txs_result = await session.execute(
            select(Transaction).where(Transaction.user_id == user.id)
        )
        invoices_result = await session.execute(select(Invoice).where(Invoice.user_id == user.id))
        for invoice in invoices_result.scalars().all():
            await session.delete(invoice)
        for tx in txs_result.scalars().all():
            await session.delete(tx)
        await session.delete(user)
        await session.commit()

    asyncio.run(_with_session(scenario))


@pytest.mark.asyncio
async def test_list_invoices_endpoint(register_user, base_url: str) -> None:
    response, payload = await register_user()
    tokens = response.json()["tokens"]

    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    ) as client:
        invoices_resp = await client.get("/api/v1/billing/invoices")
    assert invoices_resp.status_code == 200
    assert isinstance(invoices_resp.json(), list)
