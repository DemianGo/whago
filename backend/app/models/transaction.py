"""
Modelo de transações financeiras dos usuários.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .plan import Plan
    from .credit import CreditLedger


class TransactionType(str, enum.Enum):
    """Tipos de transações aceitas."""

    SUBSCRIPTION = "subscription"
    CREDIT_PURCHASE = "credit_purchase"
    ADJUSTMENT = "adjustment"


class TransactionStatus(str, enum.Enum):
    """Status possíveis de uma transação."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Transaction(Base):
    """Registro de transações de billing."""

    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("reference_code", name="uq_transactions_reference_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(
            TransactionType,
            name="transaction_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(
            TransactionStatus,
            name="transaction_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=TransactionStatus.PENDING,
    )
    amount: Mapped[Numeric] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="transactions")
    plan: Mapped[Optional["Plan"]] = relationship()
    credit_entries: Mapped[list["CreditLedger"]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
    )


__all__ = ("Transaction", "TransactionType", "TransactionStatus")


