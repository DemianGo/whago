"""
Schemas Pydantic para campanhas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..models.campaign import CampaignStatus, CampaignType, MessageStatus


class CampaignSettings(BaseModel):
    chip_ids: list[UUID] = Field(default_factory=list)
    interval_seconds: int = Field(default=10, ge=1)
    randomize_interval: bool = False
    schedule_window_start: Optional[datetime] = None
    schedule_window_end: Optional[datetime] = None
    retry_attempts: int = Field(default=0, ge=0, le=3)
    retry_interval_seconds: int = Field(default=60, ge=30)


class CampaignCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: CampaignType = CampaignType.SIMPLE
    message_template: str = Field(min_length=1)
    message_template_b: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    settings: Optional[CampaignSettings] = None

    model_config = {"extra": "forbid"}


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    message_template: Optional[str] = Field(default=None, min_length=1)
    message_template_b: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    settings: Optional[CampaignSettings] = None

    model_config = {"extra": "forbid"}


class CampaignSummary(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    type: CampaignType
    status: CampaignStatus
    total_contacts: int
    sent_count: int
    delivered_count: int
    read_count: int
    failed_count: int
    credits_consumed: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CampaignDetail(CampaignSummary):
    message_template: str
    message_template_b: Optional[str]
    settings: Optional[dict]
    scheduled_for: Optional[datetime]


class ContactUploadResponse(BaseModel):
    total_processed: int
    valid_contacts: int
    invalid_contacts: int
    duplicated: int
    preview: list[dict]


class CampaignActionResponse(BaseModel):
    status: CampaignStatus
    message: str


class CampaignMessageResponse(BaseModel):
    id: UUID
    contact_id: UUID
    phone_number: str
    status: MessageStatus
    content: str
    failure_reason: Optional[str]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


__all__ = (
    "CampaignSettings",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignSummary",
    "CampaignDetail",
    "ContactUploadResponse",
    "CampaignActionResponse",
    "CampaignMessageResponse",
)


