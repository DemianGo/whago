"""
Modelo de dados para planos de assinatura WHAGO.

Segue especificações do PRD, incluindo limites e recursos por plano.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class PlanTier(str, enum.Enum):
    """Níveis principais de planos comercializados."""

    FREE = "FREE"
    BUSINESS = "BUSINESS"
    ENTERPRISE = "ENTERPRISE"


class Plan(Base):
    """Tabela `plans` com limites e recursos configuráveis."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tier: Mapped[PlanTier] = mapped_column(
        Enum(
            PlanTier,
            name="plan_tier",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    price: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    max_chips: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    monthly_messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    features: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
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

    users: Mapped[List["User"]] = relationship(back_populates="plan", cascade="all,delete")


__all__ = ("Plan", "PlanTier")


