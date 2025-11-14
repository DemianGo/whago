"""Admin Schemas"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# Admin Schemas
class AdminBase(BaseModel):
    role: str = Field(..., pattern="^(super_admin|financeiro|suporte)$")
    permissions: dict | None = None
    is_active: bool = True


class AdminCreate(AdminBase):
    email: EmailStr
    password: str = Field(..., min_length=8)


class AdminUpdate(BaseModel):
    role: str | None = Field(None, pattern="^(super_admin|financeiro|suporte)$")
    permissions: dict | None = None
    is_active: bool | None = None


class AdminResponse(AdminBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    user_email: str
    user_name: str

    class Config:
        from_attributes = True


# Dashboard Stats
class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    suspended_users: int
    mrr: float
    messages_today: int
    messages_month: int
    churn_rate: float
    new_users_7d: int
    new_users_30d: int
    total_chips: int


# User Management
class UserListItem(BaseModel):
    id: UUID
    name: str
    email: str
    plan_name: str
    credits: int
    is_active: bool
    is_suspended: bool
    created_at: datetime


class UserDetail(UserListItem):
    phone: str | None
    company_name: str | None
    document: str | None
    subscription_id: str | None
    subscription_status: str | None
    subscription_gateway: str | None
    last_login_at: datetime | None


class UserCreateAdmin(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=3)
    phone: str | None = None
    company_name: str | None = None
    plan_id: int | None = None
    credits: int | None = None
    is_active: bool = True
    is_suspended: bool = False

    
class UserUpdateAdmin(BaseModel):
    name: str | None = None
    phone: str | None = None
    company_name: str | None = None
    plan_id: int | None = None
    credits: int | None = None
    is_active: bool | None = None
    is_suspended: bool | None = None


# Plan Schemas
class PlanCreateUpdate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    slug: str = Field(..., min_length=3, max_length=50)
    tier: int
    price: float = Field(..., ge=0)
    max_chips: int = Field(..., ge=0)
    monthly_messages: int = Field(..., ge=0)
    features: dict
    is_active: bool = True


# Coupon Schemas
class CouponBase(BaseModel):
    code: str = Field(..., min_length=3, max_length=50)
    discount_type: str = Field(..., pattern="^(percentage|fixed)$")
    discount_value: float = Field(..., gt=0)
    max_uses: int | None = Field(None, ge=1)
    valid_from: datetime
    valid_until: datetime | None = None
    is_active: bool = True


class CouponCreate(CouponBase):
    pass


class CouponUpdate(BaseModel):
    discount_type: str | None = Field(None, pattern="^(percentage|fixed)$")
    discount_value: float | None = Field(None, gt=0)
    max_uses: int | None = None
    valid_until: datetime | None = None
    is_active: bool | None = None


class CouponResponse(CouponBase):
    id: UUID
    times_used: int
    created_at: datetime

    class Config:
        from_attributes = True


# Transaction Schemas
class TransactionListItem(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    type: str
    amount: float
    status: str
    payment_method: str
    reference_code: str | None
    created_at: datetime


class TransactionDetail(TransactionListItem):
    plan_id: int | None
    credits: int
    extra_data: dict | None
    processed_at: datetime | None


# Gateway Config Schemas
class GatewayConfigUpdate(BaseModel):
    is_enabled: bool | None = None
    is_active_mode_production: bool | None = None
    sandbox_config: dict | None = None
    production_config: dict | None = None


class GatewayConfigResponse(BaseModel):
    id: UUID
    gateway: str
    name: str
    is_enabled: bool
    is_active_mode_production: bool
    sandbox_config: Optional[dict] = None
    production_config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Audit Log
class AuditLogResponse(BaseModel):
    id: UUID
    admin_id: UUID
    admin_name: str
    action: str
    entity_type: str | None
    entity_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime

    class Config:
        from_attributes = True

