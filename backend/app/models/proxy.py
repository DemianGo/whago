"""
Modelos de dados para sistema de proxies residenciais.

Gerencia provedores de proxy, pool de proxies, atribuições a chips e logs de uso.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    BigInteger,
    Numeric,
    Date,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ProxyProvider(Base):
    """Tabela `proxy_providers` - Provedores de proxy (Smartproxy, etc)."""

    __tablename__ = "proxy_providers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # residential, datacenter, mobile
    credentials: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )  # {"server": "...", "port": 3120, "username": "...", "password": "...", "api_key": "..."}
    cost_per_gb: Mapped[Numeric] = mapped_column(
        Numeric(10, 4), nullable=False, default=25.00
    )  # R$/GB
    region: Mapped[str] = mapped_column(String(10), nullable=False, default="BR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    proxies: Mapped[list["Proxy"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class Proxy(Base):
    """Tabela `proxies` - Pool de proxies disponíveis."""

    __tablename__ = "proxies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("proxy_providers.id", ondelete="CASCADE")
    )
    proxy_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # rotating, static
    proxy_url: Mapped[str] = mapped_column(
        String, nullable=False
    )  # URL completa ou template com {session}
    region: Mapped[str] = mapped_column(String(10), nullable=False, default="BR")
    protocol: Mapped[str] = mapped_column(
        String(20), nullable=False, default="http"
    )  # http, https, socks5
    health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    total_bytes_used: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    provider: Mapped["ProxyProvider"] = relationship(back_populates="proxies")
    assignments: Mapped[list["ChipProxyAssignment"]] = relationship(
        back_populates="proxy"
    )


class ChipProxyAssignment(Base):
    """Tabela `chip_proxy_assignments` - Associação chip <> proxy."""

    __tablename__ = "chip_proxy_assignments"
    __table_args__ = (UniqueConstraint("chip_id", name="uq_chip_proxy_chip_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    chip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chips.id", ondelete="CASCADE")
    )
    proxy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True
    )
    session_identifier: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Sticky session ID
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    chip: Mapped["Chip"] = relationship(back_populates="proxy_assignment")
    proxy: Mapped[Optional["Proxy"]] = relationship(back_populates="assignments")


class ProxyUsageLog(Base):
    """Tabela `proxy_usage_logs` - Logs de tráfego por chip."""

    __tablename__ = "proxy_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    chip_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chips.id", ondelete="SET NULL"), nullable=True
    )
    proxy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True
    )
    bytes_sent: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    bytes_received: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cost: Mapped[Numeric] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    session_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    session_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class UserProxyCost(Base):
    """Tabela `user_proxy_costs` - Agregação mensal de custos por usuário."""

    __tablename__ = "user_proxy_costs"
    __table_args__ = (UniqueConstraint("user_id", "month", name="uq_user_proxy_costs_user_month"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_cost: Mapped[Numeric] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


__all__ = (
    "ProxyProvider",
    "Proxy",
    "ChipProxyAssignment",
    "ProxyUsageLog",
    "UserProxyCost",
)

