"""
Serviço responsável por gerenciar assinaturas e disparos de webhooks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Callable, Iterable
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.webhook import WebhookDeliveryLog, WebhookEvent, WebhookSubscription

HeadersFactory = Callable[[WebhookSubscription, str], dict[str, str]]


class WebhookService:
    """Encapsula regras de envio de eventos externos."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self.session = session
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=10.0))

    async def create_subscription(
        self,
        *,
        user_id: UUID,
        url: str,
        events: Iterable[WebhookEvent | str],
        secret: str | None = None,
        is_active: bool = True,
    ) -> WebhookSubscription:
        subscription = WebhookSubscription(
            user_id=user_id,
            url=url,
            secret=secret,
            events=[(event.value if isinstance(event, WebhookEvent) else str(event)) for event in events],
            is_active=is_active,
        )
        self.session.add(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        return subscription

    async def list_active(self, user_id: UUID) -> list[WebhookSubscription]:
        result = await self.session.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.user_id == user_id,
                WebhookSubscription.is_active.is_(True),
            )
        )
        return result.scalars().all()

    async def dispatch(
        self,
        *,
        user_id: UUID,
        event: WebhookEvent | str,
        payload: dict,
    ) -> int:
        """Dispara um evento para todas as assinaturas ativas do usuário."""

        event_value = event.value if isinstance(event, WebhookEvent) else str(event)
        subscriptions = [
            subscription
            for subscription in await self.list_active(user_id)
            if not subscription.events or event_value in (subscription.events or [])
        ]
        if not subscriptions:
            return 0

        timestamp = datetime.now(timezone.utc).isoformat()
        body = {
            "event": event_value,
            "timestamp": timestamp,
            "data": payload,
        }
        body_bytes = json.dumps(body, default=str).encode("utf-8")
        deliveries: list[WebhookDeliveryLog] = []

        async with self._client_factory() as client:
            for subscription in subscriptions:
                headers = self._build_headers(subscription, event_value, body_bytes)
                status_code: int | None = None
                success = False
                response_snippet: str | None = None
                try:
                    response = await client.post(
                        subscription.url,
                        content=body_bytes,
                        headers=headers,
                    )
                    await response.aread()
                    status_code = response.status_code
                    success = 200 <= response.status_code < 300
                    response_snippet = response.text[:1000] if response.text else None
                except Exception as exc:  # noqa: BLE001
                    response_snippet = str(exc)[:1000]

                deliveries.append(
                    WebhookDeliveryLog(
                        subscription_id=subscription.id,
                        user_id=subscription.user_id,
                        event=event_value,
                        url=subscription.url,
                        payload=body,
                        status_code=status_code,
                        success=success,
                        response_body=response_snippet,
                    )
                )

                subscription.last_delivery_at = datetime.now(timezone.utc)
                if success:
                    subscription.failure_count = 0
                else:
                    subscription.failure_count = (subscription.failure_count or 0) + 1

        self.session.add_all(deliveries)
        await self.session.commit()
        return sum(1 for delivery in deliveries if delivery.success)

    async def list_subscriptions(self, user_id: UUID) -> list[WebhookSubscription]:
        result = await self.session.execute(
            select(WebhookSubscription)
            .where(WebhookSubscription.user_id == user_id)
            .order_by(WebhookSubscription.created_at.desc())
        )
        return result.scalars().all()

    async def delete_subscription(self, user_id: UUID, subscription_id: UUID) -> None:
        subscription = await self.session.get(WebhookSubscription, subscription_id)
        if subscription is None or subscription.user_id != user_id:
            raise ValueError("Assinatura não encontrada.")
        await self.session.delete(subscription)
        await self.session.commit()

    async def get_recent_logs(self, user_id: UUID, limit: int = 20) -> list[WebhookDeliveryLog]:
        result = await self.session.execute(
            select(WebhookDeliveryLog)
            .where(WebhookDeliveryLog.user_id == user_id)
            .order_by(WebhookDeliveryLog.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def test_event(
        self,
        *,
        user_id: UUID,
        subscription_id: UUID,
        event: WebhookEvent | str,
        payload: dict,
    ) -> int:
        subscription = await self.session.get(WebhookSubscription, subscription_id)
        if subscription is None or subscription.user_id != user_id:
            raise ValueError("Assinatura não encontrada.")
        if not subscription.is_active:
            raise ValueError("Assinatura está desativada.")
        return await self.dispatch(user_id=user_id, event=event, payload=payload)

    def _build_headers(
        self,
        subscription: WebhookSubscription,
        event: str,
        body: bytes,
    ) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "WHAGO-Webhooks/1.0",
            "X-Webhook-Event": event,
        }
        if subscription.secret:
            signature = hmac.new(
                subscription.secret.encode("utf-8"),
                msg=body,
                digestmod=hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature
        return headers


__all__ = ("WebhookService", "WebhookEvent")


