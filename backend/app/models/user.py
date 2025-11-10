"""
Modelo de usuário seguindo as especificações do PRD.

Inclui campos obrigatórios, relacionamento com planos e metadados de segurança.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import List

from ..database import Base
from .plan import Plan
from .webhook import WebhookSubscription, WebhookDeliveryLog
from .transaction import Transaction
from .credit import CreditLedger
from .chip import Chip
from .campaign import Campaign
from .notification import Notification
from .audit_log import AuditLog


class User(Base):
    """Tabela `users` para autenticação e billing."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    document: Mapped[str | None] = mapped_column(String(18), nullable=True)

    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    pending_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    plan: Mapped[Plan | None] = relationship(
        back_populates="users",
        foreign_keys=[plan_id],
    )
    pending_plan: Mapped[Plan | None] = relationship(
        foreign_keys=[pending_plan_id],
    )
    default_payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_customer_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    billing_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tokens: Mapped[List["UserToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[List[Transaction]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    credit_entries: Mapped[List[CreditLedger]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chips: Mapped[List[Chip]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    campaigns: Mapped[List[Campaign]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications: Mapped[List[Notification]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()",
    )
    audit_logs: Mapped[List[AuditLog]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="AuditLog.created_at.desc()",
    )
    webhooks: Mapped[List[WebhookSubscription]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    webhook_deliveries: Mapped[List[WebhookDeliveryLog]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_renewal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_payment_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    billing_suspension_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


__all__ = ("User",)


