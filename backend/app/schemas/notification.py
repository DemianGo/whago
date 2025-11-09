"""Schemas para notificações in-app."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: UUID
    title: str
    message: Optional[str]
    type: str = Field(description="Tipo da notificação (info, success, warning, error).")
    extra_data: Optional[dict]
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]

    model_config = {"from_attributes": True}


class NotificationMarkReadRequest(BaseModel):
    notification_ids: list[UUID] = Field(default_factory=list)


class NotificationCountResponse(BaseModel):
    unread: int


__all__ = (
    "NotificationResponse",
    "NotificationMarkReadRequest",
    "NotificationCountResponse",
)
