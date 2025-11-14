"""Schemas para gerenciamento de chaves de API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyBase(BaseModel):
    id: UUID
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    is_active: bool

    model_config = {"from_attributes": True}


class ApiKeyResponse(ApiKeyBase):
    """Resposta padrão para listagem de chaves."""


class ApiKeyCreateResponse(ApiKeyBase):
    key: str = Field(description="Valor completo da API Key. Exibido apenas no momento da criação.")


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)


__all__ = ("ApiKeyResponse", "ApiKeyCreateResponse", "ApiKeyCreateRequest")
