"""Schemas de auditoria."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    description: Optional[str]
    extra_data: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogQuery(BaseModel):
    action: Optional[str] = Field(default=None, description="Filtra pelo nome da ação.")
    entity_type: Optional[str] = None
    user_id: Optional[UUID] = None


__all__ = ("AuditLogResponse", "AuditLogQuery")
