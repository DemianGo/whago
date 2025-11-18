"""Tarefas Celery para billing recorrente."""

from __future__ import annotations

import asyncio

from celery import shared_task

from app.database import AsyncSessionLocal
from app.services.billing_service import BillingService


async def _run_cycle() -> None:
    async with AsyncSessionLocal() as session:
        service = BillingService(session)
        await service.process_subscription_cycle()
        await service.process_pending_downgrades()


@shared_task(name="billing.process_subscription_cycle")
def process_subscription_cycle_task() -> None:
    """Executa as rotinas de cobrança recorrente e downgrades pendentes."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run_cycle())
    finally:
        loop.close()
