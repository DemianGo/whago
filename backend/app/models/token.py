"""
Modelos relacionados a tokens de autenticação e recuperação de senha.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class TokenType(str, enum.Enum):
    """Tipos de token rastreados no sistema (valores em minúsculo)."""

    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"


class UserToken(Base):
    """Tabela de tokens associados aos usuários."""

    __tablename__ = "user_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_user_tokens_token_hash"),
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
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    token_type: Mapped[TokenType] = mapped_column(
        Enum(
            TokenType,
            name="token_type",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    consumed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    user: Mapped["User"] = relationship(back_populates="tokens")

    @property
    def is_active(self) -> bool:
        """Retorna True se o token não está expirado, consumido ou revogado."""

        now = datetime.now(timezone.utc)
        if self.revoked_at or self.consumed_at:
            return False
        return self.expires_at > now


__all__ = ("UserToken", "TokenType")


