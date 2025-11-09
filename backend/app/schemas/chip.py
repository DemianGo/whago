"""
Schemas Pydantic para operações com chips.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..models.chip import ChipEventType, ChipStatus


class ChipEventResponse(BaseModel):
    id: UUID
    type: ChipEventType
    description: str
    extra_data: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChipResponse(BaseModel):
    id: UUID
    alias: str
    session_id: str
    phone_number: Optional[str]
    status: ChipStatus
    health_score: int
    extra_data: Optional[dict]
    created_at: datetime
    updated_at: datetime
    connected_at: Optional[datetime]
    last_activity_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ChipCreate(BaseModel):
    alias: str = Field(min_length=3, max_length=100)

    model_config = {"extra": "forbid"}


class ChipQrResponse(BaseModel):
    qr: Optional[str] = None
    expires_at: Optional[datetime] = None


__all__ = ("ChipCreate", "ChipResponse", "ChipEventResponse", "ChipQrResponse")


