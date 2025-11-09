"""Schemas para visualização de mensagens enviadas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MessageLogResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    campaign_name: str
    status: str
    recipient: str
    chip_alias: Optional[str]
    variant: Optional[str]
    failure_reason: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]

    model_config = {"from_attributes": True}


__all__ = ("MessageLogResponse",)
