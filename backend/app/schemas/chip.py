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
    qr: Optional[str] = Field(None, alias="qr_code")
    expires_at: Optional[datetime] = None
    status: Optional[str] = None
    message: Optional[str] = None
    
    model_config = {"populate_by_name": True}


class ChipHeatUpStage(BaseModel):
    stage: int
    duration_hours: int
    messages_per_hour: int
    description: str


class ChipHeatUpResponse(BaseModel):
    chip_id: UUID
    message: str
    stages: list[ChipHeatUpStage]
    recommended_total_hours: int


class ChipHeatUpGroupRequest(BaseModel):
    """Request para iniciar heat-up em grupo de chips."""
    chip_ids: list[UUID] = Field(..., min_length=2, max_length=10, description="IDs dos chips que vão aquecer juntos (mínimo 2)")
    custom_messages: list[str] | None = Field(None, description="Mensagens customizadas (opcional)")


class ChipHeatUpGroupResponse(BaseModel):
    """Response do heat-up em grupo."""
    group_id: UUID
    chip_ids: list[UUID]
    message: str
    stages: list[ChipHeatUpStage]
    recommended_total_hours: int
    preview_messages: list[str]


__all__ = (
    "ChipCreate",
    "ChipResponse",
    "ChipEventResponse",
    "ChipQrResponse",
    "ChipHeatUpStage",
    "ChipHeatUpResponse",
    "ChipHeatUpGroupRequest",
    "ChipHeatUpGroupResponse",
)


