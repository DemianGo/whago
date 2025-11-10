"""
Rotas para configuração de webhooks pelos usuários Enterprise.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.user import User
from ..schemas.webhook import (
    WebhookDeliveryLogResponse,
    WebhookSubscriptionRequest,
    WebhookSubscriptionResponse,
    WebhookTestRequest,
)
from ..services.webhook_service import WebhookEvent, WebhookService

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


async def _ensure_webhooks_enabled(session: AsyncSession, user: User) -> None:
    await session.refresh(user, attribute_names=["plan"])
    if not user.plan:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Atualize seu plano para habilitar webhooks.",
        )
    features = user.plan.features or {}
    if not features.get("webhooks"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu plano atual não possui suporte a webhooks.",
        )
    return user.plan


@router.get("", response_model=list[WebhookSubscriptionResponse])
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[WebhookSubscriptionResponse]:
    await _ensure_webhooks_enabled(session, current_user)
    service = WebhookService(session)
    subscriptions = await service.list_subscriptions(current_user.id)
    return [WebhookSubscriptionResponse.model_validate(sub) for sub in subscriptions]


@router.post("", response_model=WebhookSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_webhook(
    payload: WebhookSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WebhookSubscriptionResponse:
    await _ensure_webhooks_enabled(session, current_user)
    service = WebhookService(session)
    existing = await service.list_subscriptions(current_user.id)
    if existing:
        subscription = existing[0]
        subscription.url = str(payload.url)
        subscription.secret = payload.secret
        subscription.events = list(payload.events)
        subscription.is_active = payload.is_active
        await session.commit()
        await session.refresh(subscription)
    else:
        subscription = await service.create_subscription(
            user_id=current_user.id,
            url=str(payload.url),
            events=payload.events,
            secret=payload.secret,
            is_active=payload.is_active,
        )
    return WebhookSubscriptionResponse.model_validate(subscription)


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_webhook(
    subscription_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    await _ensure_webhooks_enabled(session, current_user)
    service = WebhookService(session)
    try:
        subscription_uuid = UUID(subscription_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador inválido.",
        ) from exc
    try:
        await service.delete_subscription(current_user.id, subscription_uuid)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/test", response_model=dict)
async def trigger_test_event(
    payload: WebhookTestRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await _ensure_webhooks_enabled(session, current_user)
    try:
        event = WebhookEvent(payload.event)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evento informado é inválido.",
        ) from exc
    service = WebhookService(session)
    try:
        delivered = await service.test_event(
            user_id=current_user.id,
            subscription_id=payload.subscription_id,
            event=event,
            payload=payload.payload or {"source": "whago.test"},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return {"delivered": delivered}


@router.get("/logs", response_model=list[WebhookDeliveryLogResponse])
async def list_delivery_logs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[WebhookDeliveryLogResponse]:
    await _ensure_webhooks_enabled(session, current_user)
    service = WebhookService(session)
    logs = await service.get_recent_logs(current_user.id)
    return [WebhookDeliveryLogResponse.model_validate(log) for log in logs]


__all__ = ("router",)

