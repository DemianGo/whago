"""
Modelos relacionados aos chips de WhatsApp gerenciados pela plataforma.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ChipStatus(str, enum.Enum):
    """Estados possíveis de um chip, conforme PRD."""

    WAITING_QR = "waiting_qr"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    MATURING = "maturing"
    BANNED = "banned"
    MAINTENANCE = "maintenance"


class Chip(Base):
    """Tabela principal de chips."""

    __tablename__ = "chips"
    __table_args__ = (
        UniqueConstraint("alias", name="uq_chips_alias"),
        UniqueConstraint("session_id", name="uq_chips_session_id"),
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
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[ChipStatus] = mapped_column(
        Enum(
            ChipStatus,
            name="chip_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ChipStatus.WAITING_QR,
    )
    health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="chips")
    events: Mapped[list["ChipEvent"]] = relationship(
        back_populates="chip",
        cascade="all, delete-orphan",
    )


class ChipEventType(str, enum.Enum):
    """Tipos de eventos registrados para um chip."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    STATUS_CHANGE = "status_change"
    MESSAGE_SENT = "message_sent"
    MESSAGE_FAILED = "message_failed"
    SYSTEM = "system"


class ChipEvent(Base):
    """Log de eventos/telemetria dos chips."""

    __tablename__ = "chip_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chips.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[ChipEventType] = mapped_column(
        Enum(
            ChipEventType,
            name="chip_event_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    chip: Mapped[Chip] = relationship(back_populates="events")


__all__ = ("Chip", "ChipStatus", "ChipEvent", "ChipEventType")


