"""
Modelo de ledger de créditos dos usuários.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .transaction import Transaction
    from .user import User


class CreditSource(str, enum.Enum):
    """Origem dos créditos lançados."""

    WELCOME = "welcome"
    PURCHASE = "purchase"
    ADJUSTMENT = "adjustment"
    CONSUMPTION = "consumption"
    REFUND = "refund"


class CreditLedger(Base):
    """Lançamentos de crédito/débito para cada usuário."""

    __tablename__ = "credit_ledger"

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
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[CreditSource] = mapped_column(
        Enum(CreditSource, name="credit_source", native_enum=False),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="credit_entries")
    transaction: Mapped["Transaction | None"] = relationship(back_populates="credit_entries")


__all__ = ("CreditLedger", "CreditSource")


