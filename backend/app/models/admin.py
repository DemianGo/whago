"""
Admin Model

Gerenciamento de administradores do sistema.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .user import User


class AdminRole(str):
    """Roles de administrador"""
    SUPER_ADMIN = "super_admin"
    FINANCEIRO = "financeiro"
    SUPORTE = "suporte"


class Admin(Base):
    """
    Modelo de Admin - Administradores do sistema
    """
    __tablename__ = "admins"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=AdminRole.SUPORTE)
    permissions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", backref="admin_profile", foreign_keys=[user_id])
    created_by: Mapped["Admin"] = relationship("Admin", remote_side=[id], foreign_keys=[created_by_id])
    audit_logs: Mapped[list["AdminAuditLog"]] = relationship("AdminAuditLog", back_populates="admin", foreign_keys="AdminAuditLog.admin_id")

    def __repr__(self):
        return f"<Admin {self.id} - {self.role}>"


class AdminAuditLog(Base):
    """
    Log de auditoria de ações administrativas
    """
    __tablename__ = "admin_audit_logs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    admin_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    admin: Mapped["Admin"] = relationship("Admin", back_populates="audit_logs", foreign_keys=[admin_id])

    def __repr__(self):
        return f"<AdminAuditLog {self.action} by {self.admin_id}>"

