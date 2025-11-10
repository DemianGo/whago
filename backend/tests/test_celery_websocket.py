"""Testes de integração para tarefas Celery e WebSocket de campanhas."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import httpx
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import websockets

from app.config import settings
from app.database import AsyncSessionLocal, DATABASE_URL
from app.models.plan import Plan
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User
from app.services.billing_service import BillingService
from tests.conftest import SYNC_ENGINE


_ASYNC_TEST_ENGINE = create_async_engine(
    DATABASE_URL,
    future=True,
)
AsyncTestSessionLocal = async_sessionmaker(
    bind=_ASYNC_TEST_ENGINE,
    expire_on_commit=False,
)


def _random_user_payload() -> dict[str, str | None]:
    unique = uuid4().hex[:8]
    number_suffix = str(uuid4().int)[-8:]
    return {
        "email": f"test-user-{unique}@example.com",
        "name": f"Usuário Teste {unique}",
        "password": "SenhaForte!1",
        "phone": f"+55119{number_suffix}",
        "company_name": "Empresa Teste",
        "document": None,
        "plan_slug": "free",
    }


def _prepare_subscription_user_sync(user_id: UUID) -> None:
    with Session(SYNC_ENGINE) as session:
        user = session.get(User, user_id)
        if user is None:
            raise AssertionError("Usuário não encontrado para preparação do teste")
        plan = session.execute(select(Plan).where(Plan.slug == "business")).scalar_one_or_none()
        if plan is None:
            raise AssertionError("Plano BUSINESS não está disponível na base")
        user.plan = plan
        user.subscription_renewal_at = datetime.now(timezone.utc) - timedelta(days=1)
        user.default_payment_method = "card"
        user.billing_customer_reference = "TEST-REF"
        session.commit()


async def _prepare_subscription_user(user_id: UUID) -> None:
    await asyncio.to_thread(_prepare_subscription_user_sync, user_id)


async def _execute_billing_cycle() -> None:
    async with AsyncTestSessionLocal() as session:
        service = BillingService(session)
        await service.process_subscription_cycle()
        await service.process_pending_downgrades()


def _fetch_subscription_transaction_sync(user_id: UUID) -> Transaction:
    with Session(SYNC_ENGINE) as session:
        result = session.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.SUBSCRIPTION,
            )
            .order_by(Transaction.created_at.desc())
        )
        transaction = result.scalars().first()
        if transaction is None:
            raise AssertionError("Nenhuma transação de assinatura encontrada")
        session.refresh(transaction)
        return transaction


async def _fetch_subscription_transaction(user_id: UUID) -> Transaction:
    return await asyncio.to_thread(_fetch_subscription_transaction_sync, user_id)


def _fetch_user_sync(user_id: UUID) -> User:
    with Session(SYNC_ENGINE) as session:
        user = session.get(User, user_id)
        if user is None:
            raise AssertionError("Usuário não encontrado após processamento")
        session.refresh(user, attribute_names=["plan"])
        return user


async def _fetch_user(user_id: UUID) -> User:
    return await asyncio.to_thread(_fetch_user_sync, user_id)


async def _wait_for_api(base_url: str = "http://localhost:8000", timeout: float = 30.0) -> None:
    start = time.monotonic()
    while True:
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=2.0) as client:
                response = await client.get("/health")
            if response.status_code < 500:
                return
        except Exception:
            pass
        if time.monotonic() - start > timeout:
            raise TimeoutError("API não respondeu dentro do tempo limite.")
        await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_billing_celery_cycle_processes_subscription(register_user) -> None:
    await _wait_for_api()
    response, _ = await register_user()
    assert response.status_code == 201, response.text
    user_id = UUID(response.json()["user"]["id"])

    await _prepare_subscription_user(user_id)
    await _execute_billing_cycle()

    transaction = await _fetch_subscription_transaction(user_id)
    assert transaction.status == TransactionStatus.COMPLETED
    assert transaction.attempt_count >= 1

    user = await _fetch_user(user_id)
    assert user.subscription_renewal_at is not None
    assert user.subscription_renewal_at > datetime.now(timezone.utc)


async def _publish_campaign_update(campaign_id: UUID, payload: str) -> None:
    redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        await redis.publish(f"{settings.redis_campaign_updates_channel}:{campaign_id}", payload)
    finally:
        await redis.aclose()


async def _create_campaign_async(client, headers: dict[str, str]) -> UUID:
    payload = {
        "name": "Campanha Realtime",
        "description": "Teste de websocket",
        "type": "simple",
        "message_template": "Olá {{name}}",
        "settings": {"chip_ids": [], "interval_seconds": 10, "randomize_interval": False},
    }
    response = await client.post("/api/v1/campaigns/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


@pytest.mark.asyncio
async def test_campaign_websocket_receives_updates(register_user, async_client_factory) -> None:
    await _wait_for_api()
    response, _ = await register_user()
    assert response.status_code == 201, response.text
    tokens = response.json()["tokens"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    async with async_client_factory() as client:
        campaign_id = await _create_campaign_async(client, headers)

    ws_headers = [(name, value) for name, value in headers.items()]
    async with websockets.connect(
        f"ws://localhost:8000/api/v1/campaigns/ws/{campaign_id}",
        extra_headers=ws_headers,
        open_timeout=10,
    ) as websocket:
        initial_raw = await asyncio.wait_for(websocket.recv(), timeout=10)
        initial = json.loads(initial_raw)
        assert initial["type"] == "initial_state"
        assert initial["campaign_id"] == str(campaign_id)

        update_payload = json.dumps(
            {
                "type": "progress",
                "campaign_id": str(campaign_id),
                "sent": 5,
                "delivered": 3,
            }
        )
        await asyncio.sleep(0.5)
        await _publish_campaign_update(campaign_id, update_payload)
        received = await asyncio.wait_for(websocket.recv(), timeout=10)
        assert received == update_payload
