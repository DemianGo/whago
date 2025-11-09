"""Serviço responsável por registrar e listar logs de auditoria."""

from __future__ import annotations

from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit_log import AuditLog


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        *,
        user_id: UUID | None,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        description: str | None = None,
        extra_data: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        auto_commit: bool = False,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            extra_data=extra_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(log)
        if auto_commit:
            await self.session.commit()
            await self.session.refresh(log)
        else:
            await self.session.flush()
        return log

    async def list_logs(
        self,
        *,
        user_id: UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


__all__ = ("AuditService",)
