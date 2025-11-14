"""
Modelos relacionados a campanhas e mensagens.
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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .user import User
    from .chip import Chip


class CampaignType(str, enum.Enum):
    SIMPLE = "simple"
    PERSONALIZED = "personalized"
    AB_TEST = "ab_test"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class MessageStatus(str, enum.Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Campaign(Base):
    """Campanha de envio de mensagens."""

    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_campaigns_user_name"),
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
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    type: Mapped[CampaignType] = mapped_column(
        Enum(
            CampaignType,
            name="campaign_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=CampaignType.SIMPLE,
    )
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(
            CampaignStatus,
            name="campaign_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=CampaignStatus.DRAFT,
    )
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    message_template_b: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    total_contacts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    read_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credits_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="campaigns")
    contacts: Mapped[list["CampaignContact"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["CampaignMessage"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    media: Mapped[list["CampaignMedia"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


class CampaignContact(Base):
    """Contatos importados para uma campanha."""

    __tablename__ = "campaign_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    variables: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    campaign: Mapped[Campaign] = relationship(back_populates="contacts")
    messages: Mapped[list["CampaignMessage"]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
    )


class CampaignMessage(Base):
    """Mensagens geradas a partir de uma campanha."""

    __tablename__ = "campaign_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign_contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    chip_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chips.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variant: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(
            MessageStatus,
            name="campaign_message_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=MessageStatus.PENDING,
    )
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    campaign: Mapped[Campaign] = relationship(back_populates="messages")
    contact: Mapped[CampaignContact] = relationship(back_populates="messages")
    chip: Mapped[Optional["Chip"]] = relationship()


class CampaignMedia(Base):
    """Arquivos de mídia anexados à campanha."""

    __tablename__ = "campaign_media"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
    )

    campaign: Mapped[Campaign] = relationship(back_populates="media")


__all__ = (
    "Campaign",
    "CampaignContact",
    "CampaignMessage",
    "CampaignMedia",
    "CampaignType",
    "CampaignStatus",
    "MessageStatus",
)


