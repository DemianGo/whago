"""
Schemas Pydantic para sistema de proxies.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ========== ProxyProvider Schemas ==========

class ProxyProviderBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    provider_type: str = Field(..., description="residential, datacenter, mobile")
    credentials: Dict[str, Any] = Field(..., description="Credenciais do provedor")
    cost_per_gb: Decimal = Field(default=25.00, description="Custo por GB em R$")
    region: str = Field(default="BR", max_length=10)
    is_active: bool = True


class ProxyProviderCreate(ProxyProviderBase):
    pass


class ProxyProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    provider_type: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    cost_per_gb: Optional[Decimal] = None
    region: Optional[str] = None
    is_active: Optional[bool] = None


class ProxyProviderResponse(ProxyProviderBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== Proxy Schemas ==========

class ProxyBase(BaseModel):
    provider_id: UUID
    proxy_type: str = Field(..., description="rotating ou static")
    proxy_url: str = Field(..., description="URL completa ou template")
    region: str = Field(default="BR")
    protocol: str = Field(default="http")
    health_score: int = Field(default=100, ge=0, le=100)
    is_active: bool = True


class ProxyCreate(ProxyBase):
    pass


class ProxyUpdate(BaseModel):
    proxy_type: Optional[str] = None
    proxy_url: Optional[str] = None
    region: Optional[str] = None
    protocol: Optional[str] = None
    health_score: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class ProxyResponse(ProxyBase):
    id: UUID
    total_bytes_used: int
    last_health_check: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== ChipProxyAssignment Schemas ==========

class ChipProxyAssignmentResponse(BaseModel):
    id: UUID
    chip_id: UUID
    proxy_id: Optional[UUID]
    session_identifier: Optional[str]
    assigned_at: datetime
    released_at: Optional[datetime]

    class Config:
        from_attributes = True


# ========== ProxyUsageLog Schemas ==========

class ProxyUsageLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    chip_id: Optional[UUID]
    proxy_id: Optional[UUID]
    bytes_sent: int
    bytes_received: int
    total_bytes: int
    cost: Decimal
    session_start: datetime
    session_end: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ========== UserProxyCost Schemas ==========

class UserProxyCostResponse(BaseModel):
    id: UUID
    user_id: UUID
    month: date
    total_bytes: int
    total_cost: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== Dashboard/Stats Schemas ==========

class ProxyUsageStatsResponse(BaseModel):
    """Estatísticas de uso de proxy para dashboard."""
    bytes_used: int = Field(..., description="Bytes usados no período")
    gb_used: float = Field(..., description="GB usados (calculado)")
    cost: Decimal = Field(..., description="Custo em R$")
    limit_gb: Decimal = Field(..., description="Limite do plano em GB")
    percentage_used: float = Field(..., description="% do limite usado")


__all__ = [
    "ProxyProviderBase",
    "ProxyProviderCreate",
    "ProxyProviderUpdate",
    "ProxyProviderResponse",
    "ProxyBase",
    "ProxyCreate",
    "ProxyUpdate",
    "ProxyResponse",
    "ChipProxyAssignmentResponse",
    "ProxyUsageLogResponse",
    "UserProxyCostResponse",
    "ProxyUsageStatsResponse",
]

