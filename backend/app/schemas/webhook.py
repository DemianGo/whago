"""
Schemas Pydantic para configuração de webhooks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence
from uuid import UUID

from pydantic import BaseModel, HttpUrl, Field

from ..models.webhook import WebhookEvent


class WebhookSubscriptionRequest(BaseModel):
    """Payload para criação/atualização de webhooks."""

    url: HttpUrl
    secret: str | None = Field(default=None, max_length=255)
    events: Sequence[str] = Field(default_factory=list)
    is_active: bool = True


class WebhookSubscriptionResponse(BaseModel):
    """Representação da assinatura."""

    id: UUID
    url: HttpUrl
    events: list[str]
    is_active: bool
    secret: str | None = None
    created_at: datetime
    updated_at: datetime
    last_delivery_at: datetime | None = None
    failure_count: int

    model_config = {"from_attributes": True}


class WebhookDeliveryLogResponse(BaseModel):
    """Resposta para logs de entregas."""

    id: UUID
    subscription_id: UUID
    event: str
    status_code: int | None
    success: bool
    response_body: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookTestRequest(BaseModel):
    """Payload para envio de evento de teste."""

    subscription_id: UUID
    event: str = WebhookEvent.CAMPAIGN_STARTED.value
    payload: dict = Field(default_factory=dict)


__all__ = (
    "WebhookSubscriptionRequest",
    "WebhookSubscriptionResponse",
    "WebhookDeliveryLogResponse",
    "WebhookTestRequest",
)

